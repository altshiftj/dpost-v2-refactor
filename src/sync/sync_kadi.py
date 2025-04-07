import os
from dataclasses import dataclass
from typing import Optional

from src.config.settings import (
    DEVICE_TYPE, DEVICE_ID, DEVICE_USER_ID, DEVICE_RECORD_ID,
    DEFAULT_REM_RECORD_DESCRIPTION, ID_SEP, LOG_FILE
)
from src.ui.ui_abstract import UserInterface
from src.ui.ui_messages import ErrorMessages
from src.records.local_record import LocalRecord
from src.sync.sync_abstract import ISyncManager

from kadi_apy import KadiManager
from kadi_apy.lib.resources.records import Record as KadiRecord
from kadi_apy.lib.resources.groups import Group as KadiGroup
from kadi_apy.lib.resources.users import User as KadiUser

from src.app.logger import setup_logger

logger = setup_logger(__name__)

# Define a dataclass to hold all the sync resources.
@dataclass
class SyncResources:
    db_user: Optional[KadiUser]        # May be None if not found.
    user_group: KadiGroup              # The user's raw data group.
    device_user: KadiUser              # The device account user.
    device_group: KadiGroup            # The device raw data group.
    db_record: KadiRecord              # The database record (created or retrieved).

class KadiSyncManager(ISyncManager):
    """
    Concrete implementation of ISyncManager that handles synchronization of local records
    to a remote database using KadiManager.
    """

    def __init__(self, ui: UserInterface):
        """
        Initializes the SyncManager with a database manager instance.
        UI dependency is injected.
        """
        self.db_manager = KadiManager()
        self.ui = ui

    def sync_record_to_database(self, local_record: LocalRecord):
        """
        Synchronizes a LocalRecord object to the remote database.
        The workflow is:
          1. Prepare all sync resources (user, groups, record).
          2. Initialize the record if not already in the database.
          3. Upload pending files.
          4. Mark the local record as synced.
        """
        try:
            with self.db_manager as db_manager:
                # Prepare all required resources as a SyncResources dataclass.
                resources = self._prepare_resources(db_manager, local_record)
                # Initialize the record if it's not in the DB.
                self._initialize_new_db_record(
                    local_record=local_record,
                    db_record=resources.db_record,
                    db_user=resources.db_user,
                    db_device_user=resources.device_user,
                    db_user_group=resources.user_group,
                    db_device_data_group=resources.device_group
                )
                # Upload any pending files.
                self._upload_record_files(resources.db_record, local_record)
                # Mark the local record as synced.
                local_record.is_in_db = True
                logger.info(f"All files for record '{local_record.identifier}' have been synced to the database.")
        except Exception as e:
            logger.exception(f"Failed to upload files to the database: {e}")
            raise e

    def _prepare_resources(self, db_manager: KadiManager, local_record: LocalRecord) -> SyncResources:
        """
        Prepares and returns a SyncResources object that encapsulates all resources needed for syncing.
        
        Uses information already present in the local_record (user, institute, sample_name)
        as well as lookups via db_manager.
        """
        # Retrieve the user based on local_record.
        db_user: KadiUser = self._get_db_user_from_local_record(db_manager, local_record)
        # Get or create the user rawdata group.
        user_group: KadiGroup = self._get_or_create_db_user_rawdata_group(db_manager, local_record, db_user)
        # Retrieve the device user.
        device_user: KadiUser = db_manager.user(username=DEVICE_ID, identity_type='local')
        # Get or create the device rawdata group.
        device_group: KadiGroup = self._get_or_create_db_device_rawdata_group(db_manager)
        # Retrieve or create the database record.
        db_record: KadiRecord = self._get_or_create_db_record(db_manager, local_record)
        
        return SyncResources(
            db_user=db_user,
            user_group=user_group,
            device_user=device_user,
            device_group=device_group,
            db_record=db_record
        )

    def _get_or_create_group(self, db_manager: KadiManager, group_id: str, title: str, add_user_info: dict = None) -> KadiGroup:
        """
        A helper that retrieves a group by its identifier or creates it if not found.
        Optionally adds a user based on add_user_info.
        """
        try:
            group: KadiGroup = db_manager.group(identifier=group_id)
        except Exception:
            group: KadiGroup = db_manager.group(create=True, identifier=group_id)
            group.set_attribute('title', title)
            logger.debug(f"Created new group with ID: {group_id}")
        if add_user_info:
            group.add_user(user_id=add_user_info['user_id'], role_name=add_user_info.get('role', 'admin'))
        return group

    def _get_or_create_db_user_rawdata_group(self, db_manager: KadiManager, local_record: LocalRecord, db_user: KadiUser) -> KadiGroup:
        """
        Retrieves or creates the user raw data group based on the local_record's info.
        """
        # local_record now carries user, institute, sample_name.
        group_id = f"{local_record.user}{ID_SEP}{local_record.institute}{ID_SEP}rawdata{ID_SEP}group"
        title = f"{local_record.user.upper()}@{local_record.institute.upper()}: Raw Data Records"
        add_user_info = {"user_id": db_user.id, "role": "admin"} if db_user else None
        return self._get_or_create_group(db_manager, group_id, title, add_user_info)

    def _get_or_create_db_device_rawdata_group(self, db_manager: KadiManager) -> KadiGroup:
        """
        Retrieves or creates the device raw data group.
        """
        db_device_record = db_manager.record(id=DEVICE_RECORD_ID)
        group_id = f"{DEVICE_ID.lower()}{ID_SEP}rawdata{ID_SEP}group"
        title = f"{db_device_record.meta['title']}: Raw Data Records"
        add_user_info = {"user_id": DEVICE_USER_ID, "role": "admin"}
        return self._get_or_create_group(db_manager, group_id, title, add_user_info)

    def _get_or_create_db_record(self, db_manager: KadiManager, local_record: LocalRecord) -> KadiRecord:
        """
        Creates or retrieves a database record for the local_record.
        """
        db_record: KadiRecord = db_manager.record(create=True, identifier=local_record.identifier)
        return db_record

    def _get_db_user_from_local_record(self, db_manager: KadiManager, local_record: LocalRecord) -> KadiUser:
        """
        Retrieves the database user corresponding to the local_record.
        If not found, alerts the operator via the UI and returns None.
        """
        # Use the already extracted user and institute from local_record.
        db_user_id = f"{local_record.user}{ID_SEP}{local_record.institute}"
        try:
            db_user: KadiUser = db_manager.user(username=db_user_id, identity_type='local')
        except Exception:
            self.ui.show_error(
                ErrorMessages.USER_NOT_FOUND.format(user_id=db_user_id),
                ErrorMessages.USER_NOT_FOUND_DETAILS.format(user_id=db_user_id)
            )
            db_user = None
        return db_user

    def _initialize_new_db_record(
        self,
        local_record: LocalRecord,
        db_record: KadiRecord,
        db_user: KadiUser,
        db_device_user: KadiUser,
        db_user_group: KadiGroup,
        db_device_data_group: KadiGroup
    ):
        """
        Initializes the database record with attributes, tags, links, and group roles
        if it has not yet been marked as synced.
        """
        if not local_record.is_in_db:
            db_record.set_attribute('title', local_record.sample_name)
            db_record.set_attribute('description', DEFAULT_REM_RECORD_DESCRIPTION)
            db_record.set_attribute('type', 'rawdata')
            db_record.add_tag('Electron Microscopy')
            db_record.add_tag(local_record.datatype)
            db_record.link_record(DEVICE_RECORD_ID, 'generated by')
            db_record.add_group_role(group_id=db_user_group.id, role_name='member')
            db_record.add_group_role(group_id=db_device_data_group.id, role_name='member')
            db_record.add_user(user_id=db_device_user.id, role_name='admin')
            if db_user:
                db_record.add_user(user_id=db_user.id, role_name='admin')
            logger.debug(f"Initialized new database record '{local_record.identifier}' with attributes and tags.")

    def _upload_record_files(self, db_record: KadiRecord, local_record: LocalRecord):
        """
        Uploads any pending files from local_record to the database.
        Marks each file as uploaded, and removes missing files.
        """
        missing_files = []
        for file_path, uploaded in local_record.files_uploaded.items():
            if not uploaded:
                try:
                    db_record.upload_file(file_path)
                    local_record.files_uploaded[file_path] = True
                    logger.debug(f"Uploaded file: {os.path.basename(file_path)}")
                except FileNotFoundError:
                    logger.warning(f"File not found: {os.path.basename(file_path)}")
                    missing_files.append(file_path)
                    continue
                except Exception as e:
                    logger.exception(f"Failed to upload file: {os.path.basename(file_path)}")
                    raise e
        for file_path in missing_files:
            del local_record.files_uploaded[file_path]
            logger.debug(f"Removed missing file '{os.path.basename(file_path)}' from local record.")

    def sync_logs_to_database(self):
        """
        Synchronizes the log file to the database.
        """
        with self.db_manager as db_manager:
            db_record: KadiRecord = db_manager.record(id=DEVICE_RECORD_ID)
            db_record.upload_file(LOG_FILE, force=True)
        logger.info("Uploaded log file to the database.")
