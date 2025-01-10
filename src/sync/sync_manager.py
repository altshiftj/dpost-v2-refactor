import os
from abc import ABC, abstractmethod

from src.records.local_record import LocalRecord
from src.gui.user_interface import UserInterface
from src.app.logger import setup_logger
from src.config.settings import DEVICE_ID, DEVICE_RECORD_ID, DEFAULT_REM_RECORD_DESCRIPTION, ID_SEP

from kadi_apy import KadiManager
from kadi_apy.lib.resources.records import Record as KadiRecord
from kadi_apy.lib.resources.groups import Group as KadiGroup
from kadi_apy.lib.resources.users import User as KadiUser

logger = setup_logger(__name__)


class ISyncManager(ABC):
    """
    Interface for managing synchronization operations between local records and the database.
    
    This abstract base class defines the essential methods that any synchronization manager
    implementation must provide. It ensures consistency and standardization across different
    synchronization processes within the application.
    """

    @abstractmethod
    def sync_record_to_database(self, local_record: LocalRecord):
        """
        Synchronize a local record to the database.

        Args:
            local_record (LocalRecord): The local record to synchronize.
        """
        pass


class SyncManager(ISyncManager):
    """
    Concrete implementation of ISyncManager that handles synchronization of local records
    to a remote database using KadiManager.
    """

    def __init__(self, db_manager, ui: UserInterface):
        """
        Initializes the SyncManager with a database manager instance.

        Args:
            db_manager (callable): A factory or context manager that provides an instance
                                   of KadiManager for database operations.
        """
        self.db_manager: KadiManager = db_manager
        self.ui = ui

    def sync_record_to_database(self, local_record: LocalRecord):
        """
        Synchronizes a LocalRecord object to the remote database.
        """
        try:
            with self.db_manager as db_manager:  # Step 1: Connect to DB
                db_manager: KadiManager

                # 1. Retrieve the user (show error if not found; creation not supported yet)
                db_user = self._get_db_user(db_manager, local_record)

                # 2. Retrieve or create the user group
                db_user_group = self._get_or_create_db_user_group(db_manager, local_record, db_user)

                # 3. Retrieve or create the record
                db_record = self._get_or_create_db_record(db_manager, local_record)

                # 4. Retrieve or create the device data group
                db_device_data_group = self._get_or_create_db_device_data_group(db_manager)

                # 5. Initialize record if it's newly created
                self._initialize_new_db_record(
                    db_record=db_record,
                    local_record=local_record,
                    db_user=db_user,
                    db_user_group=db_user_group,
                    db_device_data_group=db_device_data_group
                )

                # 6. Upload files and mark them as uploaded
                self._upload_record_files(db_record, local_record)

                # 7. Mark the LocalRecord as existing in the database
                local_record.is_in_db = True
                logger.info(f"All files for record '{local_record.long_id}' "
                            f"have been synced to the database.")

        except Exception as e:
            logger.exception(f"Failed to upload files to the database: {e}")
            raise e

    def _get_or_create_db_user_group(
        self, 
        db_manager: KadiManager, 
        local_record: LocalRecord,
        db_user: KadiUser
    ) -> KadiGroup:
        """
        Retrieves or creates a user group for this record based on user/institute info.
        If user is provided, also adds the user to the group as 'admin'.
        """
        institute, user_initials = local_record.short_id.split(ID_SEP)[:2]
        db_group_id = f"{user_initials}{ID_SEP}{institute}{ID_SEP}rawdata{ID_SEP}group"

        try:
            db_group: KadiGroup = db_manager.group(identifier=db_group_id)
        except:
            # Group not found, create it
            db_group: KadiGroup = db_manager.group(create=True, identifier=db_group_id)
            db_group.set_attribute('title', f"{user_initials.upper()}@{institute.upper()}: Raw Data Records")
            logger.debug(f"Created new user group with ID: {db_group_id}")

        # If the group was just created or retrieved without the user, ensure the user is added
        if db_user:
            db_group.add_user(user_id=db_user.id, role_name='admin')
            db_group.remove_user(user_id=db_manager.pat_user.id)

        return db_group

    def _get_or_create_db_device_data_group(self, db_manager: KadiManager) -> KadiGroup:
        """
        Retrieves or creates the device data group, linking it to the device record ID.
        """
        db_device_record = db_manager.record(id=DEVICE_RECORD_ID)

        db_group_id = f"{DEVICE_ID.lower()}-rawdata-group"

        try:
            db_group: KadiGroup = db_manager.group(identifier=db_group_id)
        except:
            db_group: KadiGroup = db_manager.group(create=True, identifier=db_group_id)
            db_group.set_attribute('title', f"{db_device_record.meta['title']}: Raw Data Records")
            logger.debug(f"Created new device data group with ID: {db_group_id}")

        return db_group

    def _get_or_create_db_record(self, db_manager: KadiManager, local_record: LocalRecord) -> KadiRecord:
        """
        Create a new record in the database or retrieve it if it already exists.
        """
        # Using create=True ensures that if the record does not exist, it’s created.
        db_record: KadiRecord = db_manager.record(
            create=True, 
            identifier=local_record.long_id
        )
        return db_record

    def _get_db_user(self, db_manager: KadiManager, local_record: LocalRecord) -> KadiUser:
        """
        Retrieve the user object for this record. If the user doesn't exist, 
        show an error in the UI, and return None. (Creation is not supported yet.)
        """
        institute, user_initials = local_record.short_id.split(ID_SEP)[:2]
        db_user_id = f"{user_initials}{ID_SEP}{institute}"

        try:
            db_user: KadiUser = db_manager.user(username=db_user_id, identity_type='local')
        except:
            self.ui.show_error(
                f"User {db_user_id} not found", 
                f"User not found in kadi4mat database.\n"
                f"Records will be uploaded now, and later associated with the {db_user_id} "
                f"account when it is created.\nPlease contact your administrator."
            )
            db_user = None

        return db_user

    def _initialize_new_db_record(
        self, 
        db_record: KadiRecord, 
        local_record: LocalRecord, 
        db_user: KadiUser, 
        db_user_group: KadiGroup, 
        db_device_data_group: KadiGroup
    ):
        """
        If the local_record isn't in the DB yet, set up the new database record's attributes,
        tags, and links.
        """
        if not local_record.is_in_db:
            db_record.set_attribute('title', local_record.name)
            db_record.set_attribute('description', DEFAULT_REM_RECORD_DESCRIPTION)
            db_record.set_attribute('type', 'rawdata')
            db_record.add_tag('Electron Microscopy')

            # Add the datatype extracted from the local_record's long_id
            datatype = local_record.long_id.split(ID_SEP)[3]
            db_record.add_tag(datatype)

            # Link the record to the device record
            db_record.link_record(DEVICE_RECORD_ID, 'generated by')

            # Ensure group roles
            db_record.add_group_role(group_id=db_user_group.id, role_name='admin')
            db_record.add_group_role(group_id=db_device_data_group.id, role_name='admin')

            # Optionally assign user roles as well
            if db_user:
                db_record.add_user(user_id=db_user.id, role_name='admin')

            logger.debug(f"Initialized new database record '{local_record.long_id}' with attributes and tags.")

    def _upload_record_files(self, db_record: KadiRecord, local_record: LocalRecord):
        """
        Uploads any files from the local_record that haven't been uploaded yet.
        Updates local_record.files_uploaded to mark each file as uploaded.
        """
        for file_path, uploaded in local_record.files_uploaded.items():
            if not uploaded:
                # Upload the file to the database
                db_record.upload_file(file_path)
                # Mark the file as uploaded
                local_record.files_uploaded[file_path] = True
                logger.debug(f"Uploaded file: {os.path.basename(file_path)}")
