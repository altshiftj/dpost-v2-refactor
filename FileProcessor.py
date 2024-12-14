import os
import re
import json
import datetime
import shutil
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict
from kadi_apy import KadiManager

from event_gui_session import UserInterface, GUIManager, SessionManager, SessionManagerInterface
from REM_watchdog import LocalRecord

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)  # or desired logging level

@dataclass
class RecordIdInfo:
    device_id: str = "null"
    date: str = "null"
    daily_count: int = -1
    institute: str = "null"
    user_id: str = "null"
    sample_id: str = "null"
    
@dataclass
class LocalRecord:
    id_info: RecordIdInfo
    is_in_db: bool = False
    file_uploaded: Dict[str, bool] = field(default_factory=dict)

    @property
    def long_id(self) -> str:
        return f"{self.id_info.device_id}-{self.id_info.date}-REC_{self.id_info.daily_count:03}-{self.id_info.institute}-{self.id_info.user_id}"

    @property
    def short_id(self) -> str:
        return f"{self.id_info.institute}-{self.id_info.user_id}-{self.id_info.sample_id}"
    
    @property
    def name(self) -> str:
        return self.id_info.sample_id

    def add_item(self, path: str):
        if os.path.isfile(path):
            self.file_uploaded[path] = False
        elif os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for file in files:
                    file_path = os.path.join(root, file)
                    self.file_uploaded[file_path] = False
        else:
            logger.warning(f"Path '{path}' is neither a file nor a directory.")

    def mark_uploaded(self, file_path: str):
        if file_path in self.file_uploaded:
            self.file_uploaded[file_path] = True

    def count_files(self) -> int:
        return len(self.file_uploaded)

    def all_uploaded(self) -> bool:
        return all(self.file_uploaded.values())

    def to_dict(self) -> dict:
        return {
            "record_id": self.long_id,
            "record_name": self.short_id,
            "in_db": self.is_in_db,
            "files_uploaded": self.file_uploaded,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "LocalRecord":
        return cls(
            record_name=data.get("record_name", ""),
            record_id=data.get("record_id", ""),
            is_in_db=data.get("in_db", False),
            file_uploaded=data.get("files_uploaded", {})
        )

class StorageManager:
    def __init__(self, archive_dir: str, rename_folder: str, staging_dir: str):
        self.archive_dir = archive_dir
        self.rename_folder = rename_folder
        self.staging_dir = staging_dir

    def archive_record_files(self, record: LocalRecord):
        record_dir = os.path.join(self.archive_dir, record.long_id)
        if not os.path.exists(record_dir):
            os.mkdir(record_dir)

        new_file_uploaded = {}
        for file_path, uploaded in record.file_uploaded.items():
            basename = os.path.basename(file_path)
            dest_path = os.path.join(record_dir, basename)
            if os.path.exists(dest_path):
                new_file_uploaded[dest_path] = uploaded
                continue

            try:
                os.rename(file_path, dest_path)
                new_file_uploaded[dest_path] = uploaded
                logger.info(f"Archived file '{file_path}' to '{dest_path}'.")
            except Exception as e:
                logger.exception(f"Failed to move file '{file_path}' to '{dest_path}': {e}")

        record.file_uploaded = new_file_uploaded

    def clear_staging_dir(self):
        for root, dirs, files in os.walk(self.staging_dir):
            for file in files:
                os.remove(os.path.join(root, file))
            for dir in dirs:
                shutil.rmtree(os.path.join(root, dir))

    def move_item(self, src: str, dest: str):
        try:
            os.rename(src, dest)
        except:
            shutil.move(src, dest)

    def move_to_directory(self, path: str, directory: str, log_message: str):
        new_path = os.path.join(directory, os.path.basename(path))
        self.move_item(path, new_path)
        logger.info(log_message)

    def move_to_rename_folder(self, path: str, name: str):
        counter = 1
        date_str = datetime.datetime.now().strftime('%Y%m%d')
        new_path = date_str + '_' + name + '_' + str(counter)
        new_path = os.path.join(self.rename_folder, new_path)
        while os.path.exists(new_path):
            counter += 1
            new_path = date_str + '_' + name + '_' + str(counter)
            new_path = os.path.join(self.rename_folder, new_path)
        self.move_item(path, new_path)

    def rename_elid_files(self, folder_path: str, base_name: str):
        for root, dirs, files in os.walk(folder_path):
            dirname = os.path.split(root)[-1]
            for fname in files:
                if fname.endswith('.elid') or fname.endswith('.odt'):
                    old_path = os.path.join(folder_path, fname)
                    _, ext = os.path.splitext(fname)
                    new_path = os.path.join(folder_path, base_name + ext)
                    os.rename(old_path, new_path)

                if 'analysis' in dirname and 'analysis' not in fname:
                    old_fp = os.path.join(root, fname)
                    new_basename = f'{dirname}_{fname}'
                    new_basename = new_basename.replace(' ', '-')
                    new_basename = new_basename.replace('_', '-')
                    new_fp = os.path.join(root, new_basename)
                    os.rename(old_fp, new_fp)
                    logger.info(f"Renamed '{old_fp}' to '{new_fp}' based on analysis rule.")
                
                elif " " in fname:
                    old_fp = os.path.join(root, fname)
                    new_fp = os.path.join(root, fname.replace(' ', '-'))
                    os.rename(old_fp, new_fp)
                    logger.info(f"Renamed '{old_fp}' to '{new_fp}' based on space rule.")


class NamingService:
    def __init__(self, device_id: str, staging_dir: str, input_pattern: re.Pattern):
        self.device_ID = device_id
        self.staging_dir = staging_dir
        self.input_pattern = input_pattern

    def matches_naming_convention(self, base_name: str) -> bool:
        return bool(self.input_pattern.match(base_name))

    def scrub_input(self, input_str: str) -> str:
        return re.sub(r'[^A-Za-z0-9_-]+', '_', input_str)

    def construct_names_and_id(self, base_name: str, extension: str, data_type: str, existing_basenames: str) -> (str, str, str, str):
        # Similar logic from _construct_names_and_id, using self.device_ID and current datetime
        cleaned_base = self.scrub_input(base_name)
        parts = cleaned_base.split('_')
        institute, user_ID, sample_ID = parts
        device_name = self.device_ID.split('_')[0]
        date = datetime.datetime.now().strftime('%Y%m%d')

        appended_base_name = f"{device_name}_{cleaned_base}_{date}"
        record_ID = f"{self.device_ID}-{date}-{data_type}-{institute}-{user_ID}"
        record_name = sample_ID

        new_file_path = self.get_unique_file_path(base_name, appended_base_name, extension, existing_basenames)
        return appended_base_name, record_name, record_ID, new_file_path

    def get_unique_file_path(self, base_name: str, appended_base_name: str, extension: str, existing_basenames: list[str]) -> str:
        file_count = 1

        while True:
            new_basename = f"{appended_base_name}_{file_count}{extension}"
            if new_basename not in existing_basenames:
                return os.path.join(self.staging_dir, new_basename)
            file_count += 1

    def validate_user_input_name(self, dialog_result: dict) -> (bool, str):
        if dialog_result is None:
            return False, "User cancelled the dialog."

        user_ID = dialog_result['name']
        institute = dialog_result['institute']
        sample_ID = dialog_result['sample_ID']

        if not user_ID or not institute or not sample_ID:
            return False, "All fields are required."
        return True, (user_ID, institute, sample_ID)


class RecordPersistence:
    def __init__(self, daily_records_path: str, records_db_path: str):
        self.daily_records_path = daily_records_path
        self.records_db_path = records_db_path

    def load_daily_records(self) -> dict:
        if os.path.exists(self.daily_records_path):
            try:
                with open(self.daily_records_path, 'r') as f:
                    daily_data = json.load(f)

                daily_records = {
                    base_name: LocalRecord.from_dict(record_data)
                    for base_name, record_data in daily_data.items()
                }
                return daily_records
            except Exception as e:
                logger.exception(f"Failed to load daily records: {e}")
        return {}

    def save_daily_records(self, daily_records_dict: dict):
        daily_data = {key: record.to_dict() for key, record in daily_records_dict.items()}
        try:
            with open(self.daily_records_path, 'w') as f:
                json.dump(daily_data, f, indent=4)
            logger.info("Daily records saved.")
        except Exception as e:
            logger.exception(f"Failed to save daily records: {e}")

    def append_to_records_db(self, record: LocalRecord):
        """Append a single record entry to the NDJSON records database."""
        record_id = record.long_id
        sync_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        record_name = record.short_id
        file_basenames = [os.path.basename(fp) for fp in record.file_uploaded.keys()]

        record_entry = {
            "record_id": record_id,
            "upsync_time": sync_time,
            "record_name": record_name,
            "files": file_basenames,
        }

        try:
            with open(self.records_db_path, 'a') as f:
                f.write(json.dumps(record_entry) + "\n")
            logger.info(f"Appended record '{record_id}' to records_db.ndjson.")
        except Exception as e:
            logger.exception(f"Failed to append to records_db: {e}")


class SessionController:
    def __init__(self, session_manager: SessionManager, ui: UserInterface):
        self.session_manager = session_manager
        self.ui = ui

    def manage_session(self):
        if not self.session_manager.session_active:
            self.session_manager.start_session()
            self.ui.show_done_dialog(self.session_manager)
        else:
            self.session_manager.reset_timer()


class SyncManager:
    def __init__(self, db_manager):
        # db_manager_factory could be something like KadiManager or a callable that returns a DB manager instance.
        self.db_manager_factory = db_manager

    def sync_record_to_database(self, local_record: LocalRecord):
        try:
            with self.db_manager_factory() as db_manager:
                kadi_record = db_manager.record(create=True, identifier=local_record.long_id)
                
                if not local_record.is_in_db:
                    kadi_record.set_attribute('title', local_record.short_id)

                for file_path, uploaded in local_record.file_uploaded.items():
                    if not uploaded:
                        kadi_record.upload_file(file_path)
                        local_record.file_uploaded[file_path] = True
                        logger.info(f"Uploaded file: {os.path.basename(file_path)}")
                local_record.is_in_db = True
                logger.info("Files have been synced to the database.")
        except Exception as e:
            logger.exception(f"Failed to upload files to the database: {e}")


class RecordManager:
    def __init__(self, record_persistence: RecordPersistence, device_ID: str, data_type: str):
        self.record_persistence = record_persistence
        self.device_ID = device_ID
        self.data_type = data_type
        self.daily_records_dict = self.record_persistence.load_daily_records()

    def get_or_create_record(self, record_name: str, record_ID: str, institute: str, user_id: str, date: str, in_db: bool=False) -> LocalRecord:
        daily_record_key = f"{institute}_{user_id}_{record_name}"
        if daily_record_key not in self.daily_records_dict:
            current_count = len(self.daily_records_dict) + 1
            self.daily_records_dict[daily_record_key] = LocalRecord(
                RecordIdInfo(
                    device_id=self.device_ID,
                    date=date,
                    daily_count=current_count,
                    institute=institute,
                    user_id=user_id,
                    sample_id=record_name
                ),
                is_in_db=in_db
            )
        
        return self.daily_records_dict[daily_record_key]

    def add_item_to_record(self, record_name: str, record_ID: str, path: str, institute: str, user_id: str, date: str, in_db: bool=False):
        record = self.get_or_create_record(record_name, record_ID, institute, user_id, date, in_db)
        record.add_item(path)
        self.save_records()

    def save_records(self):
        self.record_persistence.save_daily_records(self.daily_records_dict)

    def get_all_records(self) -> dict:
        return self.daily_records_dict

    def clear_all_records(self):
        self.daily_records_dict.clear()
        self.save_records()

    def get_record_by_short_id(self, short_id: str) -> LocalRecord:
        return self.daily_records_dict.get(short_id)
    
    def get_record_by_long_id(self, long_id: str) -> LocalRecord:
        for record in self.daily_records_dict.values():
            record: LocalRecord
            if record.long_id == long_id:
                return record
        return None
    
    def get_record_filepaths(self, record: LocalRecord) -> list[str]:
        return list(record.file_uploaded.items())
    
    def get_record_filepath_basenames(self, record: LocalRecord) -> list[str]:
        return [os.path.basename(fp) for fp in record.file_uploaded.keys()]


class FileProcessor:
    """
    Handles file validation, renaming, moving, and archiving.
    """
    def __init__(
            self, 
        device_ID, 
        rename_folder, 
        staging_dir, 
        archive_dir, 
        exceptions_dir, 
        input_pattern, 
        ui: UserInterface, 
        session_manager: SessionManagerInterface,
        session_controller: SessionController,
        storage_manager: StorageManager,
        naming_service: NamingService,
        record_persistence: RecordPersistence,
        sync_manager: SyncManager,
        record_manager: RecordManager
    ):
        self.device_ID = device_ID
        self.rename_folder = rename_folder
        self.staging_dir = staging_dir
        self.archive_dir = archive_dir
        self.exceptions_dir = exceptions_dir
        self.input_pattern: re.Pattern = input_pattern
        self.ui: UserInterface = ui
        self.session_manager: SessionManagerInterface = session_manager
        self.session_controller: SessionController = session_controller(session_manager, ui)
        self.storage_manager: StorageManager = storage_manager(archive_dir, rename_folder, staging_dir)
        self.naming_service: NamingService = naming_service(device_ID, staging_dir, input_pattern)
        self.record_persistence: RecordPersistence = record_persistence(os.path.join(archive_dir, 'daily_records.json'), os.path.join(archive_dir, 'records_db.ndjson'))
        self.sync_manager: SyncManager = sync_manager(KadiManager)
        self.record_manager: RecordManager = record_manager(record_persistence, device_ID, '')

        self.data_type = ''

    def archive_record_files(self, record: LocalRecord):
        self.storage_manager.archive_record_files(record)

        self.record_manager.save_records()
        self.record_manager.record_persistence.append_to_records_db(record)

    def _update_record(self, record_name, record_ID, path, in_db=False):
        parts = record_ID.split('-')
        date = parts[1]
        institute = parts[3]
        user_id = parts[4]
        
        self.record_manager.add_item_to_record(record_name, record_ID, path, institute, user_id, date, in_db)

    def get_record_dict_for_sync(self) -> dict:
        return self.record_manager.daily_records_dict()

    def clear_daily_records_dict(self):
        self.record_manager.clear_all_records()
 
    def process_incoming_path(self, path: str) -> None:
        if os.path.isfile(path):
            self._process_item(path, is_folder=False)
        elif os.path.isdir(path):
            self._process_item(path, is_folder=True)

    def _process_item(self, path: str, is_folder=False) -> None:
        name = os.path.basename(path)
        extension = "" if is_folder else os.path.splitext(name)[1]

        if not self._identify_data_type(path, is_folder):
            self.storage_manager.move_to_directory(path, self.exceptions_dir, f"Moved '{name}' to exceptions directory.")
            return

        base_name = os.path.splitext(name)[0] if not is_folder else name
        
        # Check if the file is already in the daily records, and that the record is not already in the database
        # AND all files have been uploaded
        record = self.record_manager.get_record_by_short_id(base_name)
        if record and record.is_in_db and all(record.file_uploaded.values()):
            if self.ui.prompt_append_record(base_name):
                self._attempt_rename(path, base_name, extension, is_folder, notify=False, append=True)
            else:
                self._prompt_rename(path, name, is_folder, bad_name=False, new_record=True)
        elif self.naming_service.matches_naming_convention(base_name):
            self._attempt_rename(path, base_name, extension, is_folder, notify=False)
        else:
            self._prompt_rename(path, name, is_folder)

    def _identify_data_type(self, path, is_folder):
        if not is_folder and path.lower().endswith(('.tiff', '.tif')):
            self.data_type = 'IMG'
            return True
        elif is_folder and any(f.endswith('.elid') for f in os.listdir(path)):
            self.data_type = 'ELID'
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
            is_valid, result = self.naming_service.validate_user_input_name(dialog_result)
            if not is_valid:
                if result == "User cancelled the dialog.":
                    logger.info("User cancelled the dialog.")
                    self.storage_manager.move_to_rename_folder(path, name)
                    self.ui.show_info("Operation Cancelled", "The file/folder has been moved to the rename folder.")
                    return
                else:
                    self.ui.show_warning("Incomplete Information", result)
                    continue

            user_ID, institute, sample_ID = result
            base_name = f"{institute}_{user_ID}_{sample_ID}"

            # Check if the new name is already in the daily records
            record = self.record_manager.get_record_by_short_id(base_name)
            if record:
                if self.ui.prompt_append_record(sample_ID):
                    self._attempt_rename(path, base_name, extension, is_folder, notify=False, append=False)
                else:
                    self._prompt_rename(path, name, is_folder, bad_name=False, new_record=True)
            else:
                self._attempt_rename(path, base_name, extension, is_folder)
            break

    def _attempt_rename(self, path, base_name, extension, is_folder, notify=True, append=False):
        try:
            existing_basenames = self.record_manager.get_record_filepath_basenames()
            base_filename, record_name, record_ID, new_file_path = self.naming_service.construct_names_and_id(base_name, extension, self.data_type, existing_basenames)

            self.storage_manager.move_item(path, new_file_path)
            if is_folder and self.data_type == 'ELID':
                self.storage_manager.rename_elid_files(new_file_path, base_filename)
            
            if notify:
                self.ui.show_info("Success", f"{'Folder' if is_folder else 'File'} renamed to '{os.path.basename(new_file_path)}'")
            logger.info(f"{'Folder' if is_folder else 'File'} '{path}' renamed to '{new_file_path}'.")
            self._update_and_manage_session(record_name, record_ID, new_file_path)

        except Exception as e:
            self.ui.show_error("Error", f"Failed to rename: {e}")
            self.storage_manager.move_to_rename_folder(path, base_name)

    def clear_staging_dir(self):
        self.storage_manager.clear_staging_dir()

    def _update_and_manage_session(self, record_name, record_ID, new_filepath):
        self._update_record(record_name, record_ID, new_filepath)
        self.session_controller.manage_session()
