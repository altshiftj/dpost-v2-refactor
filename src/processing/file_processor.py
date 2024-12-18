import os
import time

from src.processing.metadata_extractor import MetadataExtractor
from src.storage.storage_manager import StorageManager
from src.storage.path_manager import PathManager
from src.records.record_manager import RecordManager
from src.sync.sync_manager import SyncManager
from src.records.record_persistence import RecordPersistence
from src.records.local_record import LocalRecord
from src.gui.gui_manager import UserInterface
from src.sessions.session_controller import SessionController
from src.sessions.session_manager import SessionManagerInterface

from kadi_apy import KadiManager

from src.app.logger import setup_logger

logger = setup_logger(__name__)

class FileProcessor:
    """
    Handles file validation, renaming, moving, and archiving.
    """
    def __init__(
        self,
        ui: UserInterface, 
        session_manager: SessionManagerInterface,
    ):
        self.ui: UserInterface = ui
        self.session_manager: SessionManagerInterface = session_manager

        self.session_controller = SessionController(session_manager, ui)
        self.paths = PathManager()
        self.storage = StorageManager(self.paths)

        self.persistence = RecordPersistence()
        
        db_manager = KadiManager()
        self.sync = SyncManager(db_manager)

        self.records = RecordManager(self.persistence, self.paths)

        # If there are any records in the daily records dict that are not fully in the database
        # upon startup, sync them to the database
        if not self.records.all_records_uploaded():
            logger.info("Syncing records to database upon startup.")
            self.sync_records_to_database()

        # State set by the data type of the current item being processed
        # may be more appropriate to move this to a different class
        self.item_data_type = None

    def clear_daily_records_dict(self):
        self.records.clear_all_records()

    def is_file_complete(self, path: str, check_interval: float = 0.1, max_checks: int = 5) -> bool:
        """
        Checks if a file is fully written by monitoring its size over time.

        :param path: Path to the file to check.
        :param check_interval: Time (in seconds) between size checks.
        :param max_checks: Maximum number of size checks before giving up.
        :return: True if the file size is stable, False otherwise.
        """
        try:
            previous_size = -1
            for _ in range(max_checks):
                current_size = os.path.getsize(path)
                if current_size == previous_size:
                    return True
                previous_size = current_size
                time.sleep(check_interval)
            return False
        except FileNotFoundError:
            logger.error(f"File not found during completion check: {path}")
            return False
        except Exception as e:
            logger.error(f"Error checking if file is complete: {path}. Error: {e}")
            return False
        
    def process_item(self, path: str):
        if self.is_file_complete(path):
            name = os.path.basename(path)
            extension = os.path.splitext(name)[1]

            valid, self.item_data_type = self.is_valid_datatype(path)
            if not valid:
                exception_path = self.paths.get_exception_path(name)
                self.storage.move_item(path, exception_path)
                logger.info(f"Moved '{name}' to exceptions directory.")
                return

            base_name = os.path.splitext(name)[0]
            
            record = self.records.get_record_by_short_id(base_name)
            
            if record and record.is_in_db and record.all_files_uploaded():  
                state = 'append_to_synced'
            elif self.paths.validate_naming_convention(base_name):          
                state = 'valid_record_name'
            else:                                                           
                state = 'invalid_name'

            # Use match to handle different states
            match state:
                case 'append_to_synced':
                    if self.ui.prompt_append_record(base_name):
                        self.add_item_to_record(record, path, base_name, extension)
                    else:
                        self.prompt_item_rename(path, name, bad_name_prompt=False, new_record_prompt=True)
                
                case 'valid_record_name':
                    self.add_item_to_record(record, path, base_name, extension, notify=False)
                
                case 'invalid_name':
                    self.prompt_item_rename(path, name)
        else:
            logger.warning(f"File not complete, skipping processing: {path}")

    def is_valid_datatype(self, path):
        if path.lower().endswith(('.tiff', '.tif')):
            return True, 'IMG'
        elif any(f.endswith('.elid') for f in os.listdir(path)):
            return True, 'ELID'
        return False, None

    def prompt_item_rename(self, path, name, bad_name_prompt=True, new_record_prompt=False):
        if bad_name_prompt:
            message = (
                f"The {'folder' if os.path.isdir(path) else 'file'} '{name}' does not adhere to the naming convention.\n"
                "Format: Institute_UserName_Sample-Name"
            )
            self.ui.show_warning("Invalid Name", message)
        
        if new_record_prompt:
            message = (
                f"Please provide the name for your new record\n"
                "Format: Institute_UserName_Sample-Name"
            )
            self.ui.show_info("New Record", message)

        extension = os.path.splitext(name)[1] 

        while True:
            dialog_result = self.ui.prompt_rename()
            is_valid, result = self.paths.validate_user_input(dialog_result)
            if not is_valid:
                if result == "User cancelled the dialog.":
                    logger.info("User cancelled the dialog.")
                    self.storage.move_to_directory(path, self.paths.get_rename_path(name), f"Moved '{name}' to rename folder.")
                    self.ui.show_info("Operation Cancelled", "The file/folder has been moved to the rename folder.")
                    return
                else:
                    self.ui.show_warning("Incomplete Information", result)
                    continue

            user_ID, institute, sample_ID = result
            base_name = f"{institute}_{user_ID}_{sample_ID}"

            # Check if the new name is already in the daily records
            # if it is, and all of its files are uploaded, then this 
            # record was synced in a previous session
            record = self.records.get_record_by_short_id(base_name)
            if record and record.is_in_db and record.all_files_uploaded():
                state = 'append_to_synced'
            else:
                state = 'create_new_record'

            match state:
                case 'append_to_synced':
                    if self.ui.prompt_append_record(sample_ID):
                        self.add_item_to_record(record, path, base_name, extension, notify=False)
                    else:
                        self.prompt_item_rename(path, name, bad_name_prompt=False, new_record_prompt=True)
                
                case 'create_new_record':
                    self.add_item_to_record(record, path, base_name, extension, notify=True)
            break

    def add_item_to_record(self, record, path, base_name, extension, notify=True):
        try:
            if not record:
                record_info = self.paths.generate_new_record_info(
                    base_name=base_name, 
                    data_type=self.item_data_type, 
                    record_count=self.records.get_num_records(),
                )
                record = self.records.create_record(record_info)
            
            file_id = self.paths.generate_file_id(base_name)

            record_path = self.paths.get_record_path(record)
            os.makedirs(record_path, exist_ok=True)

            if self.item_data_type == 'ELID':
                new_file_path = os.path.join(record_path, f"{file_id}")
                self.storage.rename_and_move_elid_files(path, file_id)
                self.storage.move_item(path, new_file_path)
            else:
                new_file_path = self.paths.get_unique_filename(record_path, file_id, extension)
                self.storage.move_item(path, new_file_path)

            if notify:
                self.ui.show_info("Success", f"{'Folder' if os.path.isdir(path) else 'File'} renamed to '{os.path.basename(new_file_path)}'")
            logger.info(f"{'Folder' if os.path.isdir(path) else 'File'} '{path}' renamed to '{new_file_path}'.")
            
            self.records.add_item_to_record(new_file_path, record)
            self.session_controller.manage_session()

        except Exception as e:
            self.ui.show_error("Error", f"Failed to rename: {e}")
            path = self.paths.get_unique_filename(base_name)
            self.storage.move_to_exception_folder(path)

    def sync_records_to_database(self):
        for record in self.records.get_all_records().values():
            record: LocalRecord
            if not record.all_files_uploaded():
                self.sync.sync_record_to_database(record)
                self.records.save_records()
                self.records.persistence.append_to_records_db(record)
