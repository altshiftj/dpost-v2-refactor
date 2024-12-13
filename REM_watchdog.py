import os
import re
import sys
import json
import logging
import queue
import time
import datetime
import hashlib
import tifffile
import xmltodict
import shutil
from watchdog.observers import Observer

from kadi_apy import KadiManager
from event_gui_session import FileEventHandler, GUIManager, SessionManager

DEVICE_NAME = "REM_01"

WATCH_DIR = r"monitored_folder"
RENAME_DIR = os.path.join(WATCH_DIR, 'To_Rename')
STAGING_DIR = os.path.join(WATCH_DIR, 'Staging')
ARCHIVE_DIR = os.path.join(WATCH_DIR, 'Archive')
EXCEPTIONS_DIR = os.path.join(WATCH_DIR, 'Exceptions')
ARCHIVED_FILES_JSON = os.path.join(ARCHIVE_DIR, 'processed_files.json')

FILENAME_PATTERN = re.compile(r'^[A-Za-z0-9]+_[A-Za-z0-9]+_[A-Za-z0-9-]+$')

logging.basicConfig(filename='watchdog.log', level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


# LocalRecord represents a collection of files with the same root_name (cf record name) and their associated metadata
class LocalRecord:
    """
    Represents a collection of files for a single record.
    """
    def __init__(self, record_name, record_id, in_db=False):
        self.record_name = record_name
        self.record_id = record_id
        self.in_db = in_db
        # files: { file_path: bool }
        # True = already uploaded, False = not uploaded yet
        self.file_uploaded = {}
        self.metadata = {}

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

    def get_file_count(self):
        # Count only actual data files, excluding metadata files
        # The logic remains the same, just adapted for dictionary keys
        return len([f for f in self.file_uploaded.keys() 
                    if not f.endswith('_metadata.json') and not f.endswith('.json')])

    def upload_to_database(self):
        try:
            with KadiManager() as db_manager:
                # Create a new record in the DB
                kadi_record = db_manager.record(create=True, identifier=self.record_id)
                
                if not self.in_db:
                    kadi_record.set_attribute('title', self.record_name)
                for file_path, uploaded in self.file_uploaded.items():
                    if uploaded:
                        continue
                    kadi_record.upload_file(file_path)
                    self.file_uploaded[file_path] = True
                    logger.info(f"Uploaded file: {os.path.basename(file_path)}")
                self.in_db = True

                logger.info("Files have been synced to the database.")
        except Exception as e:
            logger.exception(f"Failed to upload files to the database: {e}")


class MetadataExtractor:
    @staticmethod
    def hash_file(file_path, chunk_size=65536):
        try:
            hasher = hashlib.sha256()
            with open(file_path, 'rb') as file:
                while True:
                    data = file.read(chunk_size)
                    if not data:
                        break
                    hasher.update(data)
            return hasher.hexdigest()
        except Exception as e:
            logger.exception(f"Failed to hash file {file_path}: {e}")
            return None

    @staticmethod
    def flatten_xml_dict(d, parent_key='', sep='_'):
        items = {}
        if parent_key.startswith('FeiImage'):
            parent_key = parent_key.replace('FeiImage', '')

        for k, v in d.items():
            if k.startswith('@'):
                attr_name = k[1:]
                new_key = f"{parent_key}{sep}{attr_name}" if parent_key else attr_name
                items[new_key] = v
            elif k == '#text':
                if v.strip():
                    new_key = parent_key if parent_key else 'text'
                    items[new_key] = v.strip()
            else:
                new_parent_key = f"{parent_key}{sep}{k}" if parent_key else k
                if isinstance(v, dict):
                    items.update(MetadataExtractor.flatten_xml_dict(v, new_parent_key, sep=sep))
                elif isinstance(v, list):
                    for i, item in enumerate(v):
                        items.update(MetadataExtractor.flatten_xml_dict(item, f"{new_parent_key}{sep}{i}", sep=sep))
                elif isinstance(v, tuple):
                    for i, item in enumerate(v):
                        items.update(MetadataExtractor.flatten_xml_dict(item, f"{new_parent_key}{sep}{i}", sep=sep))
                else:
                    new_key = new_parent_key
                    items[new_key] = v
        return items
    
    @staticmethod
    def parse_xml_metadata(xml_string):
        try:
            xml_dict = xmltodict.parse(xml_string)
            flat_dict = MetadataExtractor.flatten_xml_dict(xml_dict)
            return flat_dict
        except Exception as e:
            logger.exception(f"Failed to parse XML metadata: {e}")
            return {}

    @staticmethod
    def extract_tiff_metadata(file_path):
        base_name = os.path.basename(file_path)
        file_name, ext = os.path.splitext(base_name)
        file_hash = MetadataExtractor.hash_file(file_path)

        metadata = {}
        flattened_data = {}
        try:
            with tifffile.TiffFile(file_path) as tif:
                page = tif.pages[0]
                tags = page.tags

                for tag in tags.values():
                    tag_name = tag.name
                    tag_value = tag.value

                    if isinstance(tag_value, tuple):
                        flattened_data = {f"{tag_name}_{i}": value for i, value in enumerate(tag_value)}

                    if isinstance(tag_value, bytes):
                        try:
                            tag_value = tag_value.decode('utf-8')
                        except UnicodeDecodeError:
                            tag_value = tag_value.decode('latin-1')

                    if flattened_data:
                        metadata.update(flattened_data)
                        flattened_data = {}
                    else:
                        metadata[tag_name] = tag_value

                    if tag_name == "FEI_TITAN":
                        xml_metadata = MetadataExtractor.parse_xml_metadata(tag_value)
                        for k, v in xml_metadata.items():
                            if v is None:
                                xml_metadata[k] = 'null'
                            elif re.match(r'^-?\d+$', v):
                                xml_metadata[k] = int(v)
                            elif re.match(r'^-?\d+(\.\d+)?$', v):
                                xml_metadata[k] = float(v)
                            elif re.match(r'^-?\d+(\.\d+)?[eE][-+]?\d+$', v):
                                xml_metadata[k] = float(v)
                        metadata.update(xml_metadata)

            metadata.pop('FEI_TITAN', None)
            metadata.pop('xmlns:xsi', None)
            metadata.pop('xsi:noNamespaceSchemaLocation', None)

            metadata[f"filehash"] = file_hash
            metadata = {f"{file_name}|{k}": v for k, v in metadata.items()}

        except Exception as e:
            logger.exception(f"Failed to extract metadata from {file_path}: {e}")
            return None
        return metadata

# FileProcessor handles file validation, renaming, and moving, and interacts with the GUIManager to alert the user of naming issues
# and interacts with the SessionManager to start sessions
class FileProcessor:
    """
    Handles file validation, renaming, moving, and archiving.
    """
    def __init__(self, device_ID, rename_folder, staging_dir, archive_dir, exceptions_dir, input_pattern, gui_manager, session_manager):
        self.device_ID = device_ID
        self.rename_folder = rename_folder
        self.staging_dir = staging_dir
        self.archive_dir = archive_dir
        self.exceptions_dir = exceptions_dir
        self.input_pattern: re.Pattern = input_pattern
        self.gui_manager: GUIManager = gui_manager
        self.session_manager: SessionManager = session_manager

        self.data_type = ''
        self.daily_records_dict = {}  # {base_name: LocalRecord}
        self.daily_records_json = os.path.join(self.archive_dir, 'daily_records.json')
        self.load_daily_records()

        # Records DB in NDJSON format
        # Each line is a separate JSON object representing a record entry.
        self.records_db_path = os.path.join(self.archive_dir, 'records_db.ndjson')

    #region Data Persistence
    def load_daily_records(self):
        if os.path.exists(self.daily_records_json):
            try:
                with open(self.daily_records_json, 'r') as f:
                    daily_data = json.load(f)
                for base_name, record_data in daily_data.items():
                    lr = LocalRecord(record_data["record_name"], record_data["record_id"], record_data.get("in_db", False))
                    file_uploaded = {fp: uploaded for fp, uploaded in record_data["files_uploaded"].items()}
                    lr.file_uploaded = file_uploaded
                    self.daily_records_dict[base_name] = lr
            except Exception as e:
                logger.exception(f"Failed to load daily records: {e}")

    def save_daily_records(self):
        daily_data = {}
        for record_key, lr in self.daily_records_dict.items():
            lr: LocalRecord

            daily_data[record_key] = {
                "record_id": lr.record_id,
                "record_name": lr.record_name,
                "in_db": lr.in_db,
                "files_uploaded": lr.file_uploaded,
            }

        try:
            with open(self.daily_records_json, 'w') as f:
                json.dump(daily_data, f, indent=4)
            logger.info("Daily records saved.")
        except Exception as e:
            logger.exception(f"Failed to save daily records: {e}")

    def append_to_records_db(self, record: LocalRecord):
        # Append a single record entry as NDJSON line
        record_id = record.record_id
        sync_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        record_name = record.record_name
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
    #endregion

    #region Record Management
    def archive_record_files(self, record: LocalRecord):
        record_dir = os.path.join(self.archive_dir, record.record_id)
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
        self.save_daily_records()
        self.append_to_records_db(record)

    def _update_record(self, record_name, record_ID, path, in_db=False):
        # TODO: Make this splitting logic more robust in case the record_ID format changes in the future
        parts = record_ID.split('-')
        date = parts[1]
        institute = parts[3]
        user_id = parts[4]
        
        daily_record_key = f"{institute}_{user_id}_{record_name}"

        if daily_record_key not in self.daily_records_dict:
            # count the number of keys in daily_record_dict
            current_count = len(self.daily_records_dict)+1

            rec_part = f"REC_{current_count:03}"
            record_ID = f"{self.device_ID}-{date}-{rec_part}-{self.data_type}-{institute}-{user_id}"

            self.daily_records_dict[daily_record_key] = LocalRecord(record_name, record_ID, in_db)

        self.daily_records_dict[daily_record_key].add_item(path)
        self.save_daily_records()

    def get_record_dict_for_sync(self):
        return self.daily_records_dict

    def clear_daily_records_dict(self):
        self.daily_records_dict.clear()
        self.save_daily_records
    #endregion

    #region Processing Items
    def process_incoming_path(self, path):
        if os.path.isfile(path):
            self._process_item(path, is_folder=False)
        elif os.path.isdir(path):
            self._process_item(path, is_folder=True)

    def _process_item(self, path, is_folder=False):
        name = os.path.basename(path)
        extension = "" if is_folder else os.path.splitext(name)[1]

        if not self._identify_data_type(path, is_folder):
            self._move_to_directory(path, self.exceptions_dir, f"Invalid data type for {('folder' if is_folder else 'file')} '{name}'. Moved to exceptions.")
            return

        base_name = os.path.splitext(name)[0] if not is_folder else name
        
        # Check if the file is already in the daily records, and that the record is not already in the database
        if base_name in self.daily_records_dict and self.daily_records_dict[base_name].in_db and all(self.daily_records_dict[base_name].file_uploaded.values()):
            if self.gui_manager.prompt_append_record(base_name):
                self._attempt_rename(path, base_name, extension, is_folder, notify=False, append=True)
            else:
                self._prompt_rename(path, name, is_folder, notify=False, append=True)
        elif self._matches_naming_convention(base_name):
            self._attempt_rename(path, base_name, extension, is_folder, notify=False)
        else:
            self._prompt_rename(path, name, is_folder)
    #endregion

    #region Validation
    def _identify_data_type(self, path, is_folder):
        if not is_folder and path.lower().endswith(('.tiff', '.tif')):
            self.data_type = 'IMG'
            return True
        elif is_folder and any(f.endswith('.elid') for f in os.listdir(path)):
            self.data_type = 'ELID'
            return True
        return False

    def _matches_naming_convention(self, base_name):
        return bool(self.input_pattern.match(base_name))
    #endregion

    #region User Interaction
    def _prompt_rename(self, path, name, is_folder, notify=True, append=False):
        if notify:
            message = (
                f"The {'folder' if is_folder else 'file'} '{name}' does not adhere to the naming convention.\n"
                "Format: Institute_UserName_SampleName"
            )
            self.gui_manager.show_warning("Invalid Name", message)
        
        if append:
            message = (
                f"Please provide the name for your new record\n"
                "Format: Institute_UserName_SampleName"
            )
            self.gui_manager.show_info("New Record", message)

        extension = os.path.splitext(name)[1] if not is_folder else ""

        while True:
            dialog_result = self.gui_manager.prompt_rename()
            is_valid, result = self.validate_user_input(dialog_result)
            if not is_valid:
                if result == "User cancelled the dialog.":
                    logger.info("User cancelled the dialog.")
                    self._move_to_rename_folder(path, name)
                    self.gui_manager.show_info("Operation Cancelled", "The file/folder has been moved to the rename folder.")
                    return
                else:
                    self.gui_manager.show_warning("Incomplete Information", result)
                    continue

            user_ID, institute, sample_ID = result
            base_name = f"{institute}_{user_ID}_{sample_ID}"

            # Check if the new name is already in the daily records
            if base_name in self.daily_records_dict:
                if self.gui_manager.prompt_append_record(sample_ID):
                    self._attempt_rename(path, base_name, extension, is_folder, notify=False, append=True)
                else:
                    self._prompt_rename(path, name, is_folder, notify=False, append=True)
            else:
                self._attempt_rename(path, base_name, extension, is_folder)
            break

    def validate_user_input(self, dialog_result):
        if dialog_result is None:
            return False, "User cancelled the dialog."

        user_ID = dialog_result['name']
        institute = dialog_result['institute']
        sample_ID = dialog_result['sample_ID']

        if not user_ID or not institute or not sample_ID:
            return False, "All fields are required."
        return True, (user_ID, institute, sample_ID)
    #endregion

    #region Name Construction
    def _construct_names_and_id(self, base_name, extension):
        base_name = self._scrub_input(base_name)
        parts = base_name.split('_')

        institute, user_ID, sample_ID = parts
        device_name = self.device_ID.split('_')[0]
        date = datetime.datetime.now().strftime('%Y%m%d')

        appended_base_name = f"{device_name}_{base_name}_{date}"
        record_ID = f"{self.device_ID}-{date}-{self.data_type}-{institute}-{user_ID}"
        record_name = sample_ID

        new_file_path = self._get_unique_file_path(base_name, appended_base_name, extension)
        return appended_base_name, record_name, record_ID, new_file_path

    def _get_unique_file_path(self, base_name, appended_base_name, extension):
        file_count = 1

        if base_name not in self.daily_records_dict:
            return os.path.join(self.staging_dir, f"{appended_base_name}_{file_count}{extension}")
        
        previous_paths = [f for f in self.daily_records_dict[base_name].file_uploaded.keys()]
        previous_basenames = [os.path.basename(f) for f in previous_paths]

        while True:
            new_basename = f"{appended_base_name}_{file_count}{extension}"
            if new_basename not in previous_basenames:
                break
            file_count += 1
        
        return os.path.join(self.staging_dir, new_basename)
    #endregion

    #region Renaming
    def _attempt_rename(self, path, base_name, extension, is_folder, notify=True, append=False):
        try:
            base_filename, record_name, record_ID, new_file_path = self._construct_names_and_id(base_name, extension)

            self._move_item(path, new_file_path)
            if is_folder and self.data_type == 'ELID':
                self._rename_elid_files(new_file_path, base_filename)
                # TODO: Move into a separate function, occurs in two places and should be consolidated
                for root, dirs, files in os.walk(new_file_path):
                    dirname = os.path.split(root)[-1]
                    for fname in files:
                        if 'analysis' in dirname and 'analysis' not in fname:
                            old_fp = os.path.join(root, fname)
                            new_basename = f'{dirname}_{fname}'
                            new_basename = new_basename.replace(' ', '-')
                            new_fp = os.path.join(root, new_basename)
                            os.rename(old_fp, new_fp)
                            logger.info(f"Renamed '{old_fp}' to '{new_fp}' based on analysis rule.")
                        elif " " in fname:
                            old_fp = os.path.join(root, fname)
                            new_fp = os.path.join(root, fname.replace(' ', '-'))
                            os.rename(old_fp, new_fp)
                            logger.info(f"Renamed '{old_fp}' to '{new_fp}' based on space rule.")

            if notify:
                self.gui_manager.show_info("Success", f"{'Folder' if is_folder else 'File'} renamed to '{os.path.basename(new_file_path)}'")
            logger.info(f"{'Folder' if is_folder else 'File'} '{path}' renamed to '{new_file_path}'.")
            self._update_and_manage_session(record_name, record_ID, new_file_path)


        except Exception as e:
            self.gui_manager.show_error("Error", f"Failed to rename: {e}")
            self._move_to_rename_folder(path, os.path.basename(path))

    def _rename_elid_files(self, folder_path, base_name):
        for file in os.listdir(folder_path):
            if file.endswith('.elid') or file.endswith('.odt'):
                old_path = os.path.join(folder_path, file)
                _, ext = os.path.splitext(file)
                new_path = os.path.join(folder_path, base_name + ext)
                os.rename(old_path, new_path)
    #endregion

    #region Directory Ops
    def _move_to_directory(self, path, directory, log_message):
        new_path = os.path.join(directory, os.path.basename(path))
        self._move_item(path, new_path)
        logger.info(log_message)

    def _move_to_rename_folder(self, path, name):
        counter = 1
        date_str = datetime.datetime.now().strftime('%Y%m%d')
        new_path = date_str + '_' + name + '_' + str(counter)
        new_path = os.path.join(self.rename_folder, new_path)
        while os.path.exists(new_path):
            counter += 1
            new_path = date_str + '_' + name + '_' + str(counter)
            new_path = os.path.join(self.rename_folder, new_path)
        self._move_item(path, new_path)

    def _move_item(self, src, dest):
        try:
            os.rename(src, dest)
        except:
            shutil.move(src, dest)

    def clear_staging_dir(self):
        for root, dirs, files in os.walk(self.staging_dir):
            for file in files:
                os.remove(os.path.join(root, file))
            for dir in dirs:
                shutil.rmtree(os.path.join(root, dir))
    #endregion

    #region Session Management
    def _manage_session(self):
        if not self.session_manager.session_active:
            self.session_manager.start_session()
            self.gui_manager.show_done_dialog(self.session_manager)
        else:
            self.session_manager.reset_timer()

    def _update_and_manage_session(self, record_name, record_ID, new_filepath):
        self._update_record(record_name, record_ID, new_filepath)
        self._manage_session()
    #endregion

    #region Utility
    def _scrub_input(self, input_str):
        return re.sub(r'[^A-Za-z0-9_-]+', '_', input_str)

    def _generate_rename_filename(self, original_filename):
        _, ext = os.path.splitext(original_filename)
        date_str = datetime.datetime.now().strftime('%Y%m%d')
        new_filename = f"{self.device_ID}_rename-file_{date_str}{ext}"
        return self._get_unique_file_path(new_filename, ext)
    #endregion

class DeviceWatchdogApp:
    """
    Main application class
    """
    def __init__(
        self,
        watch_dir,
        device_name,
        rename_folder,
        staging_dir,
        archive_dir,
        exceptions_dir,
        test_path,
        session_timeout=60,
        testing=False,
    ):
        self.testing = testing
        self.test_path = test_path
        self.watch_dir = watch_dir
        self.archive_dir = archive_dir
        self.session_timeout = session_timeout

        if testing:
            for root, dirs, files in os.walk(watch_dir):
                for file in files:
                    os.remove(os.path.join(root, file))
                for dir in dirs:
                    shutil.rmtree(os.path.join(root, dir))


        self.gui_manager = GUIManager()
        self.session_manager = SessionManager(session_timeout, self.end_session, self.gui_manager.root)

        os.makedirs(rename_folder, exist_ok=True)
        os.makedirs(staging_dir, exist_ok=True)
        os.makedirs(archive_dir, exist_ok=True)
        os.makedirs(exceptions_dir, exist_ok=True)

        self.file_processor = FileProcessor(
            device_ID=device_name,
            rename_folder=rename_folder,
            staging_dir=staging_dir,
            archive_dir=archive_dir,
            exceptions_dir=exceptions_dir,
            input_pattern=FILENAME_PATTERN,
            gui_manager=self.gui_manager,
            session_manager=self.session_manager
        )

        self.event_queue = queue.Queue()
        self.session_timer = None

        self.event_handler = FileEventHandler(self.event_queue)
        self.observer = Observer()
        self.observer.schedule(self.event_handler, path=self.watch_dir, recursive=False)
        self.observer.start()
        logger.info(f"Monitoring directory: {self.watch_dir}")

        self.gui_manager.root.after(100, self.process_events)
        self.gui_manager.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.gui_manager.root.report_callback_exception = self.handle_exception

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        logger.error("An unexpected error occurred", exc_info=(exc_type, exc_value, exc_traceback))
        self.gui_manager.show_error("Application Error", "An unexpected error occurred. Please contact the administrator.")
        self.on_closing()

    def end_session(self):
        logger.info("DeviceWatchdogApp.end_session called.")
        try:
            self.sync_files_to_database()
        except Exception as e:
            logger.exception(f"An error occurred during session end: {e}")
            self.gui_manager.show_error("Session End Error", f"An error occurred during session end: {e}")
        finally:
            if hasattr(self.gui_manager, 'done_dialog') and self.gui_manager.done_dialog.winfo_exists():
                self.gui_manager.done_dialog.destroy()
            logger.info("End session logic completed.")

    def sync_files_to_database(self):
        logger.info("Syncing files to the database...")
        records_dict = self.file_processor.get_record_dict_for_sync()

        for local_record in records_dict.values():
            local_record: LocalRecord

            if local_record.in_db and all(local_record.file_uploaded.values()):
                logger.info(f"Record '{local_record.record_name}' is already in the database.")
                continue
            
            local_record.upload_to_database()
            self.file_processor.archive_record_files(local_record)

        self.file_processor.clear_staging_dir()

    def process_events(self):
        while not self.event_queue.empty():

            # wait for file/folder to be fully written
            # May need to be more dynamic in the future
            time.sleep(0.5)

            data_path = self.event_queue.get()
            self.file_processor.process_incoming_path(data_path)
        self.gui_manager.root.after(100, self.process_events)

        if self.testing:
            if os.path.isfile(self.test_path):
                shutil.copy(self.test_path, self.watch_dir)
            elif os.path.isdir(self.test_path):
                shutil.copytree(self.test_path, os.path.join(self.watch_dir, os.path.basename(self.test_path)))
            self.testing = False

        if datetime.datetime.now().hour == 0:
            self.file_processor.reset_daily_counter()
            self.file_processor.clear_daily_records_dict()

    def on_closing(self):
        if self.session_timer:
            self.session_timer.cancel()
        self.observer.stop()
        self.observer.join()
        self.gui_manager.destroy()
        logger.info("Monitoring stopped.")

    def run(self):
        try:
            self.gui_manager.root.mainloop()
        except KeyboardInterrupt:
            self.on_closing()
        except Exception:
            self.handle_exception(*sys.exc_info())


if __name__ == "__main__":
    testing = False
    test_path = r""

    logger.info("Starting Device Watchdog application...")
    app = DeviceWatchdogApp(
        watch_dir=WATCH_DIR,
        device_name=DEVICE_NAME,
        rename_folder=RENAME_DIR,
        staging_dir=STAGING_DIR,
        archive_dir=ARCHIVE_DIR,
        exceptions_dir=EXCEPTIONS_DIR,
        test_path=test_path,
        session_timeout=300,
        testing=testing,
    )
    try:
        app.run()
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
    finally:
        logger.info("Application closed.")
