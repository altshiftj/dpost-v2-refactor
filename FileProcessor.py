import os
import re
import json
import datetime
import shutil
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Tuple
from kadi_apy import KadiManager

from event_gui_session import UserInterface, SessionManagerInterface

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)  # or desired logging level

@dataclass
class RecordIdInfo:
    device_id: str = "null"
    date: str = "null"
    daily_record_count: int = -1
    data_type: str = "null"
    institute: str = "null"
    user_id: str = "null"
    sample_id: str = "null"
    
@dataclass
class LocalRecord:
    long_id: str = "null"
    short_id: str = "null"
    name: str = "null"
    is_in_db: bool = False
    file_uploaded: Dict[str, bool] = field(default_factory=dict)

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

    def all_files_uploaded(self) -> bool:
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


class PathManager:
    def __init__(
        self, 
        archive_dir: str, 
        staging_dir: str, 
        rename_dir: str, 
        exceptions_dir: str
    ):
        self.archive_dir = os.path.abspath(archive_dir)
        self.staging_dir = os.path.abspath(staging_dir)
        self.rename_dir = os.path.abspath(rename_dir)
        self.exceptions_dir = os.path.abspath(exceptions_dir)
        self.naming_pattern = re.compile(r'^[A-Za-z0-9]+_[A-Za-z0-9]+_[A-Za-z0-9-]+$')  # Define your naming convention here

        # Ensure all directories exist
        for directory in [self.archive_dir, self.staging_dir, self.rename_dir, self.exceptions_dir]:
            os.makedirs(directory, exist_ok=True)

    def scrub_input(self, input_str: str) -> str:
        """Sanitize input string to conform to naming conventions."""
        return re.sub(r'[^A-Za-z0-9_-]+', '_', input_str)

    def validate_naming_convention(self, base_name: str) -> bool:
        """Check if the base name matches the naming convention."""
        return bool(self.naming_pattern.match(base_name))
    
    def validate_user_input(self, dialog_result):
        if dialog_result is None:
            return False, "User cancelled the dialog."

        user_ID = dialog_result['name']
        institute = dialog_result['institute']
        sample_ID = dialog_result['sample_ID']

        if not user_ID or not institute or not sample_ID:
            return False, "All fields are required."
        return True, (user_ID, institute, sample_ID)

    def construct_long_id(self, id_info: RecordIdInfo) -> str:
        """Construct the long_id using RecordIdInfo."""
        return f"{id_info.device_id}-{id_info.date}-REC_{id_info.daily_record_count:03}-{id_info.institute}-{id_info.user_id}"

    def construct_short_id(self, id_info: RecordIdInfo) -> str:
        """Construct the short_id using RecordIdInfo."""
        return f"{id_info.institute}-{id_info.user_id}-{id_info.sample_id}"

    def get_archive_path(self, record: LocalRecord) -> str:
        """Get the archive directory path for a given record."""
        return os.path.join(self.archive_dir, record.long_id)

    def get_staging_path(self, filename: str) -> str:
        """Get the full path in the staging directory for a given filename."""
        return os.path.join(self.staging_dir, filename)

    def get_rename_path(self, name: str) -> str:
        """Generate a unique rename path for a given name."""
        return self._generate_unique_path(self.rename_dir, name)

    def get_exception_path(self, name: str) -> str:
        """Generate a path in the exceptions directory for a given name."""
        return self._generate_unique_path(self.exceptions_dir, name)

    def get_unique_filename(self, directory: str, base_name: str, extension: str) -> str:
        """Generate a unique filename within a specified directory."""
        counter = 1
        unique_name = f"{base_name}_{counter}{extension}"
        unique_path = os.path.join(directory, unique_name)

        while os.path.exists(unique_path):
            unique_name = f"{base_name}_{counter}{extension}"
            unique_path = os.path.join(directory, unique_name)
            counter += 1

        return unique_path

    def _generate_unique_path(self, directory: str, name: str) -> str:
        """Helper method to generate a unique file or folder path within a directory."""
        base_name, extension = os.path.splitext(name)
        unique_path = self.get_unique_filename(directory, base_name, extension)
        return unique_path

    def construct_new_file_path(
        self, 
        id_info: RecordIdInfo, 
        extension: str, 
        existing_basenames: List[str]
    ) -> Tuple[str, str]:
        """
        Construct a unique file path based on RecordIdInfo and extension.
        
        Returns:
            Tuple containing the new base name and the full file path.
        """
        base_directory = self.get_archive_path(id_info)
        os.makedirs(base_directory, exist_ok=True)

        base_name = self.construct_short_id(id_info)
        base_name = self.scrub_input(base_name)

        # Ensure uniqueness
        unique_path = self.get_unique_filename(base_directory, base_name, extension)
        unique_base_name = os.path.basename(unique_path)

        return unique_base_name, unique_path

    def parse_long_id(self, long_id: str) -> RecordIdInfo:
        """
        Parse a long_id string back into a RecordIdInfo object.
        
        Expected format: "{device_id}-{date}-REC_{daily_record_count}-{institute}-{user_id}"
        """
        pattern = r'^(?P<device_id>[A-Za-z0-9_-]+)-(?P<date>\d{8})-REC_(?P<daily_record_count>\d{3})-(?P<institute>[A-Za-z0-9_-]+)-(?P<user_id>[A-Za-z0-9_-]+)$'
        match = re.match(pattern, long_id)
        if not match:
            raise ValueError(f"Invalid long_id format: {long_id}")

        id_info = RecordIdInfo(
            device_id=match.group('device_id'),
            date=match.group('date'),
            daily_record_count=int(match.group('daily_record_count')),
            data_type="",  # Data type might need to be inferred or stored separately
            institute=match.group('institute'),
            user_id=match.group('user_id'),
            sample_id=""  # Sample ID is not included in long_id; handle accordingly
        )
        return id_info

    def construct_names_and_id(
        self, 
        base_name: str, 
        extension: str, 
        data_type: str, 
        record_count: int,
        device_id: str
    ) -> Tuple[str, RecordIdInfo, str]:
        """
        Construct names and ID based on the provided parameters.

        Parameters:
            base_name (str): The base name input.
            extension (str): File extension.
            data_type (str): Type of data (e.g., 'IMG', 'ELID').
            existing_basenames (List[str]): List of existing base names to ensure uniqueness.
            device_id (str): Device identifier.

        Returns:
            Tuple containing the appended base name, RecordIdInfo, and the unique file path.
        """
        cleaned_base = self.scrub_input(base_name)
        parts = cleaned_base.split('_')
        if len(parts) != 3:
            raise ValueError("Base name must consist of Institute_UserName_Sample-Name")

        institute, user_ID, sample_ID = parts
        device_name = device_id.split('_')[0]
        date = datetime.datetime.now().strftime('%Y%m%d')

        record_naming_info = RecordIdInfo(
            device_id=device_id,
            date=date,
            daily_record_count=record_count+1,
            data_type=data_type,
            institute=institute,
            user_id=user_ID,
            sample_id=sample_ID
        )

        appended_base_name = f"{device_name}_{cleaned_base}_{date}"

        new_file_path = self.get_unique_filename(self.staging_dir, appended_base_name, extension)
        return appended_base_name, record_naming_info, new_file_path


class StorageManager:
    def __init__(self, path_manager: PathManager):
        self.path_manager = path_manager

    def archive_record_files(self, record: LocalRecord):
        record_dir = self.path_manager.get_archive_path(record)
        os.makedirs(record_dir, exist_ok=True)

        new_file_uploaded = {}
        for src_path, uploaded in record.file_uploaded.items():
            basename = os.path.basename(src_path)
            dest_path = os.path.join(record_dir, basename)
            if os.path.exists(dest_path):
                new_file_uploaded[dest_path] = uploaded
                continue

            try:
                self.move_item(src_path, dest_path)
                new_file_uploaded[dest_path] = uploaded
                logger.info(f"Archived file '{src_path}' to '{dest_path}'.")
            except Exception as e:
                logger.exception(f"Failed to move file '{src_path}' to '{dest_path}': {e}")
                exception_path = self.path_manager.get_exception_path(basename)
                self.move_item(src_path, exception_path)
                logger.info(f"Moved '{src_path}' to exceptions directory at '{exception_path}'.")

        record.file_uploaded = new_file_uploaded

    def clear_staging_dir(self):
        staging_dir = self.path_manager.staging_dir
        for root, dirs, files in os.walk(staging_dir):
            for file in files:
                try:
                    os.remove(os.path.join(root, file))
                    logger.info(f"Removed file '{os.path.join(root, file)}' from staging.")
                except Exception as e:
                    logger.exception(f"Failed to remove file '{os.path.join(root, file)}' from staging: {e}")
            for dir in dirs:
                try:
                    shutil.rmtree(os.path.join(root, dir))
                    logger.info(f"Removed directory '{os.path.join(root, dir)}' from staging.")
                except Exception as e:
                    logger.exception(f"Failed to remove directory '{os.path.join(root, dir)}' from staging: {e}")

    def move_item(self, src: str, dest: str):
        try:
            os.rename(src, dest)
            logger.info(f"Moved '{src}' to '{dest}' using os.rename.")
        except OSError as e:
            logger.warning(f"os.rename failed for '{src}' to '{dest}': {e}. Attempting shutil.move.")
            try:
                shutil.move(src, dest)
                logger.info(f"Moved '{src}' to '{dest}' using shutil.move.")
            except Exception as e_move:
                logger.error(f"Failed to move '{src}' to '{dest}' using shutil.move: {e_move}.")
                raise e_move  # Re-raise exception after logging

    def move_to_directory(self, path: str, directory: str, log_message: str):
        basename = os.path.basename(path)
        base_name, extension = os.path.splitext(basename)
        unique_dest_path = self.path_manager.get_unique_filename(directory, base_name, extension)
        self.move_item(path, unique_dest_path)
        logger.info(log_message + f" Moved to '{unique_dest_path}'.")


    def move_to_rename_folder(self, path: str, name: str):
        unique_dest_path = self.path_manager.get_unique_filename(self.path_manager.rename_dir, name, '')
        self.move_item(path, unique_dest_path)
        logger.info(f"Moved '{path}' to rename folder at '{unique_dest_path}'.")

    def rename_elid_files(self, folder_path: str, base_name: str):
        for root, dirs, files in os.walk(folder_path):
            dirname = os.path.basename(root)
            for fname in files:
                old_path = os.path.join(root, fname)
                new_path = old_path

                # Handle .elid and .odt files
                if fname.endswith('.elid') or fname.endswith('.odt'):
                    _, ext = os.path.splitext(fname)
                    new_path = os.path.join(root, f"{base_name}{ext}")
                    try:
                        self.move_item(old_path, new_path)
                        logger.info(f"Renamed '{old_path}' to '{new_path}'.")
                    except Exception as e:
                        logger.error(f"Failed to rename '{old_path}' to '{new_path}': {e}")

                # Handle analysis directory renaming
                if 'analysis' in dirname and 'analysis' not in fname:
                    new_basename = f"{dirname}_{fname}".replace(' ', '-').replace('_', '-')
                    new_path = os.path.join(root, new_basename)
                    try:
                        self.move_item(old_path, new_path)
                        logger.info(f"Renamed '{old_path}' to '{new_path}' based on analysis rule.")
                    except Exception as e:
                        logger.error(f"Failed to rename '{old_path}' to '{new_path}' based on analysis rule: {e}")

                # Handle space in filenames
                elif " " in fname:
                    new_basename = fname.replace(' ', '-').replace('_', '-')
                    new_path = os.path.join(root, new_basename)
                    try:
                        self.move_item(old_path, new_path)
                        logger.info(f"Renamed '{old_path}' to '{new_path}' based on space rule.")
                    except Exception as e:
                        logger.error(f"Failed to rename '{old_path}' to '{new_path}' based on space rule: {e}")


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
    def __init__(self, session_manager: SessionManagerInterface, ui: UserInterface):
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
            with self.db_manager_factory as db_manager:
                db_manager: KadiManager
                db_record = db_manager.record(create=True, identifier=local_record.long_id)
                
                if not local_record.is_in_db:
                    db_record.set_attribute('title', local_record.name)

                for file_path, uploaded in local_record.file_uploaded.items():
                    if not uploaded:
                        db_record.upload_file(file_path)
                        local_record.file_uploaded[file_path] = True
                        logger.info(f"Uploaded file: {os.path.basename(file_path)}")
                local_record.is_in_db = True
                logger.info("Files have been synced to the database.")
        except Exception as e:
            logger.exception(f"Failed to upload files to the database: {e}")


class RecordManager:
    def __init__(self, persistence: RecordPersistence, path_manager: PathManager, device_ID: str, data_type: str):
        self.persistence = persistence
        self.paths = path_manager
        self.device_ID = device_ID
        self.data_type = data_type
        self.daily_records_dict = self.persistence.load_daily_records()

    def get_or_create_record(self, record_info: RecordIdInfo) -> LocalRecord:
        daily_record_key = self.paths.construct_short_id(record_info)
        if daily_record_key not in self.daily_records_dict:
            self.daily_records_dict[daily_record_key] = LocalRecord(
                long_id=self.paths.construct_long_id(record_info),
                short_id=self.paths.construct_short_id(record_info),
                name=record_info.sample_id
            )
        
        return self.daily_records_dict[daily_record_key]

    def add_item_to_record(self, path: str, record_info: RecordIdInfo, in_db: bool=False):
        record = self.get_or_create_record(record_info)
        record.add_item(path)
        self.save_records()

    def save_records(self):
        self.persistence.save_daily_records(self.daily_records_dict)

    def get_all_records(self) -> dict:
        return self.daily_records_dict

    def get_num_records(self) -> int:
        return len(self.daily_records_dict.keys())

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
        if not record:
            return []
        return [os.path.basename(fp) for fp in record.file_uploaded.keys()]


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
