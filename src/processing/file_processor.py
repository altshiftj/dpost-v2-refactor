from abc import ABC, abstractmethod
import os
import time

from src.processing.metadata_extractor import MetadataExtractor
from src.storage.storage_manager import IStorageManager
from src.storage.path_manager import PathManager
from src.records.record_manager import RecordManager
from src.sync.sync_manager import ISyncManager
from src.records.record_persistence import RecordPersistence
from src.records.local_record import LocalRecord
from src.gui.gui_manager import UserInterface
from src.sessions.session_controller import SessionController
from src.sessions.session_manager import SessionManager
from kadi_apy import KadiManager
from src.app.logger import setup_logger

logger = setup_logger(__name__)

class BaseFileProcessor(ABC):
    def __init__(
        self,
        ui: UserInterface,
        session_manager: SessionManager,
        session_controller: SessionController,
        paths: PathManager,
        storage: IStorageManager,
        persistence: RecordPersistence,
        sync: ISyncManager,
        records: RecordManager,
    ):
        self.ui: UserInterface                          = ui
        self.session_manager: SessionManager            = session_manager
        self.session_controller: SessionController      = session_controller
        self.paths: PathManager                         = paths
        self.storage: IStorageManager                   = storage
        self.persistence: RecordPersistence             = persistence
        self.sync: ISyncManager                         = sync
        self.records: RecordManager                     = records

        # Sync records on startup
        if not self.records.all_records_uploaded():
            logger.info("Syncing records to database upon startup.")
            self.sync_records_to_database()
            if not self.records.is_dict_up_to_date():
                self.clear_daily_records_dict()

        self.item_data_type = None

    def clear_daily_records_dict(self):
        self.records.clear_all_records()

    @abstractmethod
    def is_valid_datatype(self, path: str):
        pass

    def process_item(self, path: str):
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
                    self.storage.move_to_directory(path, self.paths.get_rename_path(name), 
                                                   f"Moved '{name}' to rename folder.")
                    self.ui.show_info("Operation Cancelled", 
                                      "The file/folder has been moved to the rename folder.")
                    return
                else:
                    self.ui.show_warning("Incomplete Information", result)
                    continue

            user_ID, institute, sample_ID = result
            base_name = f"{institute}_{user_ID}_{sample_ID}"

            name = f"{base_name}{extension}"

            record = self.records.get_record_by_short_id(base_name)
            if record and record.is_in_db and record.all_files_uploaded():  
                state = 'append_to_synced'
            elif self.paths.validate_naming_convention(base_name):          
                state = 'valid_record_name'
            else:                                                           
                state = 'invalid_name'

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

            new_file_path = self.device_specific_processing(
                record_path, file_id, path, base_name, extension
            )

            if notify:
                msg_type = "Folder" if os.path.isdir(path) else "File"
                self.ui.show_info("Success", 
                    f"{msg_type} renamed to '{os.path.basename(new_file_path)}'")
            
            logger.info(f"{'Folder' if os.path.isdir(path) else 'File'} '{path}' "
                        f"renamed to '{new_file_path}'.")
            
            self.records.add_item_to_record(new_file_path, record)
            self.session_controller.manage_session()

        except Exception as e:
            self.ui.show_error("Error", f"Failed to rename: {e}")
            path = self.paths.get_unique_filename(base_name)
            self.storage.move_to_exception_folder(path)

    @abstractmethod
    def device_specific_processing(
        self, record_path, file_id, source_path, base_name, extension
    ):
        raise NotImplementedError

    def sync_records_to_database(self):
        for record in self.records.get_all_records().values():
            record: LocalRecord
            if not record.all_files_uploaded():
                self.sync.sync_record_to_database(record)
                self.records.save_records()
                self.records.persistence.append_to_records_db(record)


class SEMFileProcessor(BaseFileProcessor):
    def is_valid_datatype(self, path: str):
        if path.lower().endswith(('.tiff', '.tif')):
            return True, 'IMG'
        elif any(f.endswith('.elid') for f in os.listdir(path)):
            return True, 'ELID'
        return False, None

    def device_specific_processing(
        self, record_path, file_id, source_path, base_name, extension
    ):
        if self.item_data_type == 'ELID':
            self.flatten_elid_directory(source_path, base_name)
            new_file_path = os.path.join(record_path, file_id)
            self.storage.move_item(source_path, new_file_path)
            return new_file_path
        else:
            new_file_path = self.paths.get_unique_filename(record_path, file_id, extension)
            self.storage.move_item(source_path, new_file_path)
            return new_file_path

    def flatten_elid_directory(self, folder_path: str, base_name: str):
        target_dir = folder_path 
        renamed_files = {}

        for root, dirs, files in os.walk(folder_path, topdown=False):
            for fname in files:
                old_path = os.path.join(root, fname)
                new_fname = fname

                if fname.endswith('.elid') or fname.endswith('.odt'):
                    _, ext = os.path.splitext(fname)
                    new_fname = f"{base_name}{ext}"

                dirname = os.path.basename(root)
                if 'analysis' in dirname and 'analysis' not in fname:
                    new_fname = f"{dirname}-{fname}".replace(' ', '-').replace('_', '-')

                if " " in new_fname:
                    new_fname = new_fname.replace(' ', '-').replace('_', '-')

                original_new_fname = new_fname
                counter = 1
                while (new_fname in renamed_files or 
                       os.path.exists(os.path.join(target_dir, new_fname))):
                    name_only, ext = os.path.splitext(original_new_fname)
                    new_fname = f"{name_only}_{counter}{ext}"
                    counter += 1

                renamed_files[new_fname] = True
                new_path = os.path.join(target_dir, new_fname)

                try:
                    self.storage.move_item(old_path, new_path)
                    logger.info(f"Moved and renamed '{old_path}' to '{new_path}'.")
                except Exception as e:
                    logger.error(f"Failed to move and rename '{old_path}' to '{new_path}': {e}")

            try:
                os.rmdir(root)
                logger.info(f"Removed empty directory: '{root}'.")
            except OSError:
                logger.warning(f"Directory not empty or removal error: '{root}'.")

        logger.info("All files have been moved and subdirectories eliminated.")
