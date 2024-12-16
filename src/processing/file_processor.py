import os

from src.processing.metadata_extractor import MetadataExtractor
from src.storage.storage_manager import StorageManager
from src.storage.path_manager import PathManager
from src.records.record_manager import RecordManager
from src.sync.sync_manager import SyncManager
from src.records.record_persistence import RecordPersistence
from src.records.models import LocalRecord
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
        device_id, 
        rename_folder, 
        staging_dir, 
        archive_dir, 
        exceptions_dir,
        ui: UserInterface, 
        session_manager: SessionManagerInterface,
    ):
        self.device_id = device_id
        self.ui: UserInterface = ui
        self.session_manager: SessionManagerInterface = session_manager

        self.session_controller = SessionController(session_manager, ui)
        self.paths = PathManager(archive_dir, staging_dir, rename_folder, exceptions_dir)
        self.storage = StorageManager(path_manager=self.paths)
        
        daily_records_path = os.path.join(archive_dir, 'daily_records.json')
        records_db_path = os.path.join(archive_dir, 'records_db.ndjson')
        self.persistence = RecordPersistence(daily_records_path, records_db_path)
        
        db_manager = KadiManager()
        self.sync = SyncManager(db_manager)

        self.records = RecordManager(self.persistence, self.paths, device_id, '')

    def archive_record_files(self, record: LocalRecord):
        self.storage.archive_record_files(record)

        self.records.save_records()
        self.records.persistence.append_to_records_db(record)

    def get_record_dict_for_sync(self) -> dict:
        return self.records.daily_records_dict()

    def clear_daily_records_dict(self):
        self.records.clear_all_records()
 
    def process_incoming_path(self, path: str):
        if os.path.isfile(path):
            self._process_item(path, is_folder=False)
        elif os.path.isdir(path):
            self._process_item(path, is_folder=True)

    def _process_item(self, path: str, is_folder=False):
        name = os.path.basename(path)
        extension = "" if is_folder else os.path.splitext(name)[1]

        if not self._identify_data_type(path, is_folder):
            exception_path = self.paths.get_exception_path(name)
            self.storage.move_item(path, exception_path)
            logger.info(f"Moved '{name}' to exceptions directory.")
            return

        base_name = os.path.splitext(name)[0] if not is_folder else name
        
        # Check if the file is already in the daily records, and that the record is not already in the database
        # AND all files have been uploaded
        record = self.records.get_record_by_short_id(base_name)
        if record and record.is_in_db and all(record.file_uploaded.values()):
            if self.ui.prompt_append_record(base_name):
                self._attempt_rename(path, base_name, extension, is_folder, notify=False, append=True)
            else:
                self._prompt_rename(path, name, is_folder, bad_name=False, new_record=True)
        elif self.paths.validate_naming_convention(base_name):
            self._attempt_rename(path, base_name, extension, is_folder, notify=False)
        else:
            self._prompt_rename(path, name, is_folder)

    def _identify_data_type(self, path, is_folder):
        if not is_folder and path.lower().endswith(('.tiff', '.tif')):
            self.records.data_type = 'IMG'
            return True
        elif is_folder and any(f.endswith('.elid') for f in os.listdir(path)):
            self.records.data_type = 'ELID'
            return True
        return False

    def _prompt_rename(self, path, name, is_folder, bad_name=True, new_record=False):
        if bad_name:
            message = (
                f"The {'folder' if is_folder else 'file'} '{name}' does not adhere to the naming convention.\n"
                "Format: Institute_UserName_Sample-Name"
            )
            self.ui.show_warning("Invalid Name", message)
        
        if new_record:
            message = (
                f"Please provide the name for your new record\n"
                "Format: Institute_UserName_Sample-Name"
            )
            self.ui.show_info("New Record", message)

        extension = os.path.splitext(name)[1] if not is_folder else ""

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
            record = self.records.get_record_by_short_id(base_name)
            if record:
                if self.ui.prompt_append_record(sample_ID):
                    self._attempt_rename(path, base_name, extension, is_folder, notify=False, append=False)
                else:
                    self._prompt_rename(path, name, is_folder, bad_name=False, new_record=True)
            else:
                self._attempt_rename(path, base_name, extension, is_folder)
            break

    def _attempt_rename(self, path, base_name, extension, is_folder, notify=True):
        try:
            base_filename, record_info, new_file_path = self.paths.construct_names_and_id(
                base_name=base_name, 
                extension=extension, 
                data_type=self.records.data_type, 
                record_count=self.records.get_num_records(), 
                device_id=self.device_id
            )

            self.storage.move_item(path, new_file_path)
            if is_folder and self.records.data_type == 'ELID':
                self.storage.rename_elid_files(new_file_path, base_filename)
            
            if notify:
                self.ui.show_info("Success", f"{'Folder' if is_folder else 'File'} renamed to '{os.path.basename(new_file_path)}'")
            logger.info(f"{'Folder' if is_folder else 'File'} '{path}' renamed to '{new_file_path}'.")
            
            self.records.add_item_to_record(new_file_path, record_info)
            self.session_controller.manage_session()

        except Exception as e:
            self.ui.show_error("Error", f"Failed to rename: {e}")
            path = self.paths.get_unique_filename(base_name)
            self.storage.move_to_directory(path, self.exceptions_dir, f"Moved '{base_name}' to exceptions directory.")

    def clear_staging_dir(self):
        self.storage.clear_staging_dir()

    def sync_records_to_database(self):
        for record in self.records.get_all_records().values():
            record: LocalRecord
            if not record.all_files_uploaded():
                self.sync.sync_record_to_database(record)
                self.archive_record_files(record)
