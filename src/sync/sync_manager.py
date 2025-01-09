"""
sync_manager.py

This module defines the ISyncManager interface and its concrete implementation, SyncManager.
It handles synchronization operations between local records and a remote database using the
KadiManager. The SyncManager ensures that records are properly uploaded and maintained in
the database, including handling file uploads and updating record attributes.
"""

import os
from abc import ABC, abstractmethod

from src.records.local_record import LocalRecord
from src.gui.user_interface import UserInterface
from src.app.logger import setup_logger
from src.config.settings import DEVICE_ID, DEVICE_RECORD_ID, DEFAULT_REM_RECORD_DESCRIPTION

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

    The SyncManager class provides methods to upload records and their associated files to
    the database. It ensures that records are properly created or updated in the database,
    and that all relevant files are uploaded and marked as synchronized.
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

        This method:
            1. Connects to the database using the provided db_manager.
            2. Creates or retrieves a database record based on the local_record's long_id.
            3. Creates or retrieves the corresponding group for the record.
            4. If the record is not in the database yet, sets its attributes and links it.
            5. Iterates through all associated files in the LocalRecord:
                - Uploads each file that hasn't been uploaded yet.
                - Marks the file as uploaded in the LocalRecord.
            6. Marks the LocalRecord as being in the database.

        Args:
            local_record (LocalRecord): The local record to synchronize.

        Raises:
            Exception: If any error occurs during the synchronization process.
        """
        try:
            with self.db_manager as db_manager:  # Step 1: Connect to DB
                db_manager: KadiManager

                db_user = self._retrieve_db_user(db_manager, local_record)
                db_user_group = self._retrieve_db_user_group(db_manager, local_record)

                if db_user and (db_user_group is None):
                    db_user_group = self._create_db_user_group(db_manager, local_record)
                    db_user_group.add_user(user_id=db_user.id, role_name='admin')
                    db_user_group.remove_user(user_id=db_manager.pat_user.id)

                elif db_user_group is None:
                    db_user_group = self._create_db_user_group(db_manager, local_record)
                
                # Step 2: Create or retrieve record
                db_record = self._create_or_retrieve_db_record(db_manager, local_record)

                # Step 3: Create or retrieve group
                db_device_data_group = self._create_or_retrieve_db_device_data_group(db_manager, local_record)

                # Step 4: Initialize record if it's newly created
                self._initialize_new_db_record(
                    db_record=db_record,
                    local_record=local_record,
                    db_user_group=db_user_group,
                    db_device_data_group=db_device_data_group,
                    db_user=db_user
                )

                # Step 5: Upload files and mark them as uploaded
                self._upload_record_files(db_record, local_record)

                # Step 6: Mark the LocalRecord as existing in the database
                local_record.is_in_db = True
                logger.info(f"All files for record '{local_record.long_id}' have been synced to the database.")

        except Exception as e:
            logger.exception(f"Failed to upload files to the database: {e}")
            raise e

    def _initialize_new_db_record(
        self, 
        db_record: KadiRecord, 
        local_record: LocalRecord, 
        db_user: KadiUser, 
        db_user_group: KadiGroup, 
        db_device_data_group: KadiGroup
    ):
        """
        If the local_record isn't in the DB yet, set up the new database record's attributes, tags, and links.

        Args:
            db_record (KadiRecord): The database record to initialize.
            local_record (LocalRecord): The local record containing the necessary info.
            db_group (KadiGroup): The group to associate with this record.
        """
        if not local_record.is_in_db:
            # Set essential attributes for the new database record
            db_record.set_attribute('title', local_record.name)
            db_record.set_attribute('description', DEFAULT_REM_RECORD_DESCRIPTION)
            db_record.set_attribute('type', 'rawdata')
            db_record.add_tag('Electron Microscopy')
            
            datatype = local_record.long_id.split('-')[3]
            db_record.add_tag(datatype)

            # Link the record to the device record ID with a descriptive relationship
            db_record.link_record(DEVICE_RECORD_ID, 'generated by')

            # Assign group roles
            db_record.add_group_role(group_id=db_user_group.id, role_name='admin')
            db_record.add_group_role(group_id=db_device_data_group.id, role_name='admin')

            if db_user:
                db_record.add_user(user_id=db_user.id, role_name='admin')
                db_user_group.add_user(user_id=db_user.id, role_name='admin')

            logger.debug(f"Initialized new database record '{local_record.long_id}' with attributes and tags.")

    def _upload_record_files(self, db_record: KadiRecord, local_record: LocalRecord):
            """
            Uploads any files from the local_record that haven't been uploaded yet. 
            Updates local_record.files_uploaded to mark each file as uploaded.

            Args:
                db_record (KadiRecord): The database record to which files should be uploaded.
                local_record (LocalRecord): The local record containing file paths.
            """
            for file_path, uploaded in local_record.files_uploaded.items():
                if not uploaded:
                    # Upload the file to the database
                    db_record.upload_file(file_path)
                    # Mark the file as uploaded
                    local_record.files_uploaded[file_path] = True
                    logger.debug(f"Uploaded file: {os.path.basename(file_path)}")

    def _create_or_retrieve_db_record(self, db_manager: KadiManager, local_record: LocalRecord) -> KadiRecord:
        """
        Create a new record in the database or retrieve the existing one.

        Args:
            db_manager (KadiManager): An instance of KadiManager for database operations.
            local_record (LocalRecord): The local record to synchronize.

        Returns:
            KadiRecord: The database record object.
        """
        db_record: KadiRecord = db_manager.record(create=True, identifier=local_record.long_id)
        return db_record

    def _create_db_user_group(self, db_manager: KadiManager, local_record: LocalRecord) -> KadiGroup:
        """
        Create or retrieve the appropriate group for this record.

        Extracts the institute and user_id from local_record.short_id and forms a group identifier.

        Args:
            db_manager (KadiManager): An instance of KadiManager for database operations.
            local_record (LocalRecord): The local record used to derive group information.

        Returns:
            KadiGroup: The database group object.
        """
        institute, user_initials, _ = local_record.short_id.split('_')
        db_group_id = f"{user_initials}-{institute}-rawdata-group"
        db_group: KadiGroup = db_manager.group(create=True, identifier=db_group_id)
        db_group.set_attribute('title', f"{user_initials.upper()}@{institute.upper()}: Raw Data Records")
        return db_group
    
    def _retrieve_db_user_group(self, db_manager: KadiManager, local_record: LocalRecord) -> KadiGroup:
        """
        Retrieve the appropriate group for this record.

        Extracts the institute and user_id from local_record.short_id and forms a group identifier.

        Args:
            db_manager (KadiManager): An instance of KadiManager for database operations.
            local_record (LocalRecord): The local record used to derive group information.

        Returns:
            KadiGroup: The database group object.
        """
        institute, user_initials, _ = local_record.short_id.split('_')
        db_group_id = f"{user_initials}-{institute}-rawdata-group"
        try:
            db_group: KadiGroup = db_manager.group(identifier=db_group_id)
        except:
            db_group = None

        return db_group
    
    def _create_or_retrieve_db_device_data_group(self, db_manager: KadiManager, local_record: LocalRecord) -> KadiGroup:
        """
        Create or retrieve the appropriate group for this record.

        Extracts the institute and user_id from local_record.short_id and forms a group identifier.

        Args:
            db_manager (KadiManager): An instance of KadiManager for database operations.
            local_record (LocalRecord): The local record used to derive group information.

        Returns:
            KadiGroup: The database group object.
        """
        db_device_record = db_manager.record(id=DEVICE_RECORD_ID)

        db_group_id = f"{DEVICE_ID.lower()}-rawdata-group"
        db_group: KadiGroup = db_manager.group(create=True, identifier=db_group_id)
        db_group.set_attribute('title', f"{db_device_record.meta['title']}: Raw Data Records")
        return db_group

    def _create_db_user(self, db_manager: KadiManager, local_record: LocalRecord) -> KadiUser:
        """
        Create or retrieve the appropriate user for this record.

        Extracts the user_id from local_record.short_id and forms a user identifier.

        Args:
            db_manager (KadiManager): An instance of KadiManager for database operations.
            local_record (LocalRecord): The local record used to derive user information.

        Returns:
            KadiUser: The database user object.
        """
        institute, user_initials, _ = local_record.short_id.split('_')
        db_user_id = f"{user_initials}-{institute}"
        try:
            db_user: KadiUser = db_manager.user(username=db_user_id, identity_type='local')
        except:
            self.ui.show_error(f"User {db_user_id} not found", f"User not found in kadi4mat database.\n"
                                                 f"Records will be uploaded now, and later associated with the {db_user_id} account when it is created\n"
                                                  "Please contact your administrator.")
            db_user = None

        #TODO: PLACEHOLDER Creating a user is not currently supported by the Kadi API.

        return db_user

    def _retrieve_db_user(self, db_manager: KadiManager, local_record: LocalRecord) -> KadiUser:
        """
        Retrieve the appropriate user for this record.

        Extracts the user_id from local_record.short_id and forms a user identifier.

        Args:
            db_manager (KadiManager): An instance of KadiManager for database operations.
            local_record (LocalRecord): The local record used to derive user information.

        Returns:
            KadiUser: The database user object.
        """
        institute, user_initials, _ = local_record.short_id.split('_')
        db_user_id = f"{user_initials}-{institute}"
        try:
            db_user: KadiUser = db_manager.user(username=db_user_id, identity_type='local')
        except:
            self.ui.show_error(f"User {db_user_id} not found", f"User not found in kadi4mat database.\n"
                                                 f"Records will be uploaded now, and later associated with the {db_user_id} account when it is created\n"
                                                  "Please contact your administrator.")
            db_user = None
        return db_user
