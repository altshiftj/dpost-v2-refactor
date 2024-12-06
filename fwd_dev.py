import os
import re
import sys
import json
import queue
import logging
import threading
import datetime
import hashlib
import tifffile
import tkinter as tk
import xmltodict
import shutil
from tkinter import simpledialog, messagebox
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from kadi_apy import KadiManager

# Constants and Configurations
DEVICE_NAME = "SEM"
WATCH_DIR = r"test_monitor"
RENAME_DIR = os.path.join(WATCH_DIR, 'To_Rename')
STAGING_DIR = os.path.join(WATCH_DIR, 'Staging')
ARCHIVE_DIR = os.path.join(WATCH_DIR, 'Archive')
EXCEPTIONS_DIR = os.path.join(WATCH_DIR, 'Exceptions')
ARCHIVED_FILES_JSON = os.path.join(ARCHIVE_DIR, 'processed_files.json')
FILENAME_PATTERN = re.compile(r'^[A-Za-z0-9]+_[A-Za-z0-9]+_[A-Za-z0-9]+$')
SESSION_TIMEOUT_SECONDS = 60

# Configure Logging
logging.basicConfig(filename='watchdog.log', level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


# -----------------------------------------------------------
# Utilities
# -----------------------------------------------------------

def scrub_input(input_str):
    """Replaces invalid filename chars with underscores."""
    return re.sub(r'[^A-Za-z0-9_-]+', '_', input_str)

def get_unique_path(dest_path):
    """Generates a unique file path to avoid overwrites by adding a counter."""
    directory, filename = os.path.split(dest_path)
    base, extension = os.path.splitext(filename)
    counter = 1
    unique_filename = f"{base}_{counter}{extension}"
    while os.path.exists(os.path.join(directory, unique_filename)):
        counter += 1
        unique_filename = f"{base}_{counter}{extension}"
    return os.path.join(directory, unique_filename)

def move_item(src, dest):
    """Moves a file or folder from src to dest."""
    try:
        os.rename(src, dest)
        logger.info(f"Moved '{src}' to '{dest}'.")
    except Exception as e:
        logger.exception(f"Failed to move '{src}' to '{dest}': {e}")
        raise

def is_tiff_file(filename):
    return filename.lower().endswith(('.tiff', '.tif'))

def is_valid_filename(base_name):
    return FILENAME_PATTERN.match(base_name) is not None


# -----------------------------------------------------------
# GUI Management
# -----------------------------------------------------------

class EntryWithPlaceholder(tk.Entry):
    """Tkinter entry that shows placeholder text."""
    def __init__(self, master=None, placeholder="PLACEHOLDER", color='grey', *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.placeholder = placeholder
        self.placeholder_color = color
        self.default_fg_color = self['fg']
        self.bind("<FocusOut>", self._focus_out)
        self.bind("<Key>", self._key_pressed)
        self._show_placeholder()

    def _show_placeholder(self):
        if not super().get():
            self.insert(0, self.placeholder)
            self['fg'] = self.placeholder_color

    def _hide_placeholder(self):
        if self['fg'] == self.placeholder_color:
            self.delete(0, 'end')
            self['fg'] = self.default_fg_color

    def _key_pressed(self, event):
        if self['fg'] == self.placeholder_color:
            self.delete(0, 'end')
            self['fg'] = self.default_fg_color

    def _focus_out(self, event):
        if not super().get():
            self._show_placeholder()

    def get(self):
        content = super().get()
        if self['fg'] == self.placeholder_color:
            return ''
        else:
            return content

class MultiFieldDialog(simpledialog.Dialog):
    """Custom dialog to collect Name, Institute, Sample-Name."""
    def body(self, master):
        tk.Label(master, text="Name:").grid(row=0, column=0, sticky='e', padx=5, pady=2)
        tk.Label(master, text="Institute:").grid(row=1, column=0, sticky='e', padx=5, pady=2)
        tk.Label(master, text="Sample-Name:").grid(row=2, column=0, sticky='e', padx=5, pady=2)

        self.user_ID_var = tk.StringVar()
        self.institute_var = tk.StringVar()
        self.sample_ID_var = tk.StringVar()

        self.example_user_ID = "Ex: MuS"
        self.example_institute = "Ex: IPAT"
        self.example_sample_ID = "Ex: Cathode-20XD6-SO4"

        self.name_entry = EntryWithPlaceholder(master, self.example_user_ID, textvariable=self.user_ID_var)
        self.institute_entry = EntryWithPlaceholder(master, self.example_institute, textvariable=self.institute_var)
        self.data_qualifier_entry = EntryWithPlaceholder(master, self.example_sample_ID, textvariable=self.sample_ID_var)

        self.name_entry.grid(row=0, column=1, sticky='we', padx=5, pady=2)
        self.institute_entry.grid(row=1, column=1, sticky='we', padx=5, pady=2)
        self.data_qualifier_entry.grid(row=2, column=1, sticky='we', padx=5, pady=2)

        master.grid_columnconfigure(1, weight=1)

        self.after(0, self._bring_to_front)
        return self.name_entry

    def _bring_to_front(self):
        self.lift()
        self.wm_attributes("-topmost", True)

    def apply(self):
        userID = self.user_ID_var.get()
        institute = self.institute_var.get()
        sample_ID = self.sample_ID_var.get()

        if userID == self.example_user_ID: userID = ""
        if institute == self.example_institute: institute = ""
        if sample_ID == self.example_sample_ID: sample_ID = ""

        self.result = {
            'name': userID,
            'institute': institute,
            'sample_ID': sample_ID,
        }

class GUIManager:
    """Manages all Tkinter GUI interactions."""
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.dialog_parent = tk.Toplevel(self.root)
        self.dialog_parent.withdraw()
        self.dialog_parent.attributes("-topmost", True)

    def show_warning(self, title, message):
        messagebox.showwarning(title, message, parent=self.dialog_parent)

    def show_info(self, title, message):
        messagebox.showinfo(title, message, parent=self.dialog_parent)

    def show_error(self, title, message):
        messagebox.showerror(title, message, parent=self.dialog_parent)

    def prompt_rename(self):
        dialog = MultiFieldDialog(self.root, "Rename File")
        return dialog.result

    def prompt_append_record(self, record_name):
        return messagebox.askyesno("Append to Existing Record", 
                                   f"Record '{record_name}' has been previously synced. Add file to existing record?",
                                   parent=self.dialog_parent)

    def show_done_dialog(self, end_session_callback):
        self.done_dialog = tk.Toplevel(self.root)
        self.done_dialog.title("Session Active")
        self.done_dialog.attributes("-topmost", True)
        label = tk.Label(self.done_dialog, text="A session is in progress. Click 'Done' when finished.")
        label.pack(padx=20, pady=10)
        done_button = tk.Button(self.done_dialog, text="Done", command=end_session_callback)
        done_button.pack(pady=10)
        self.done_dialog.protocol("WM_DELETE_WINDOW", lambda: None)

    def destroy(self):
        self.dialog_parent.destroy()
        self.root.destroy()


# -----------------------------------------------------------
# Session Management
# -----------------------------------------------------------

class SessionManager:
    def __init__(self, session_timeout, end_session_callback, root: tk.Tk):
        self.session_timeout = session_timeout * 1000
        self.session_active = False
        self.end_session_callback = end_session_callback
        self.root = root
        self.session_timer_id = None

    def start_session(self):
        if not self.session_active:
            self.session_active = True
            logger.info("Session started.")
            self.start_timer()

    def start_timer(self):
        if self.session_timer_id is not None:
            self.root.after_cancel(self.session_timer_id)
        self.session_timer_id = self.root.after(self.session_timeout, self.end_session)
        logger.info("Session timer started/restarted.")

    def reset_timer(self):
        if self.session_active:
            self.start_timer()

    def end_session(self):
        self.session_active = False
        if self.session_timer_id is not None:
            self.root.after_cancel(self.session_timer_id)
            self.session_timer_id = None
        logger.info("Session ended.")
        self.end_session_callback()

    def cancel(self):
        if self.session_timer_id is not None:
            self.root.after_cancel(self.session_timer_id)
            self.session_timer_id = None


# -----------------------------------------------------------
# Metadata Extraction
# -----------------------------------------------------------

class MetadataExtractor:
    @staticmethod
    def hash_file(file_path, chunk_size=65536):
        try:
            hasher = hashlib.sha256()
            with open(file_path, 'rb') as file:
                for chunk in iter(lambda: file.read(chunk_size), b''):
                    hasher.update(chunk)
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
                    items[new_parent_key] = v
        return items

    @staticmethod
    def parse_xml_metadata(xml_string):
        try:
            xml_dict = xmltodict.parse(xml_string)
            return MetadataExtractor.flatten_xml_dict(xml_dict)
        except Exception as e:
            logger.exception(f"Failed to parse XML metadata: {e}")
            return {}

    @staticmethod
    def extract_tiff_metadata(file_path):
        base_name = os.path.basename(file_path)
        file_name, _ = os.path.splitext(base_name)
        file_hash = MetadataExtractor.hash_file(file_path)
        metadata = {}
        try:
            with tifffile.TiffFile(file_path) as tif:
                page = tif.pages[0]
                for tag in page.tags.values():
                    tag_name = tag.name
                    tag_value = tag.value
                    if isinstance(tag_value, bytes):
                        try:
                            tag_value = tag_value.decode('utf-8')
                        except UnicodeDecodeError:
                            tag_value = tag_value.decode('latin-1')
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
                    else:
                        metadata[tag_name] = tag_value
            metadata.pop('FEI_TITAN', None)
            metadata.pop('xmlns:xsi', None)
            metadata.pop('xsi:noNamespaceSchemaLocation', None)
            metadata["filehash"] = file_hash
            metadata = {f"{file_name}|{k}": v for k, v in metadata.items()}
        except Exception as e:
            logger.exception(f"Failed to extract metadata from {file_path}: {e}")
            return None
        return metadata


# -----------------------------------------------------------
# LocalRecord and Database Sync
# -----------------------------------------------------------

class LocalRecord:
    def __init__(self, record_name, record_id, in_db=False):
        self.record_name = record_name
        self.record_id = record_id
        self.in_db = in_db
        self.files = []
        self.metadata = {}  # Placeholder for metadata aggregation if needed

    def add_item(self, path: str):
        if os.path.isfile(path):
            self.files.append(path)
        elif os.path.isdir(path):
            for root, _, files in os.walk(path):
                for file in files:
                    file_path = os.path.join(root, file)
                    self.files.append(file_path)
        else:
            logger.warning(f"Path '{path}' is neither a file nor a directory.")

    def archive_files(self, archive_dir):
        record_dir = os.path.join(archive_dir, self.record_id)
        if not os.path.exists(record_dir):
            os.mkdir(record_dir)
        new_paths = []
        for file_path in self.files:
            basename = os.path.basename(file_path)
            dirname = os.path.split(os.path.dirname(file_path))[-1]
            if 'analysis' in dirname and 'analysis' not in basename:
                dest_basename = f'{dirname}_{basename}'
                dest_path = os.path.join(record_dir, dest_basename)
            else:
                dest_path = os.path.join(record_dir, basename)
            try:
                os.rename(file_path, dest_path)
                new_paths.append(dest_path)
                logger.info(f"Archived '{file_path}' to '{dest_path}'.")
            except Exception as e:
                logger.exception(f"Failed to move '{file_path}' to '{dest_path}': {e}")
        self.files = new_paths

    def upload_to_database(self):
        try:
            with KadiManager() as db_manager:
                if self.in_db:
                    # TODO: Logic for updating existing record in DB
                    return
                kadi_record = db_manager.record(create=True, identifier=self.record_id)
                kadi_record.set_attribute('title', self.record_name)
                for file_path in self.files:
                    kadi_record.upload_file(file_path)
                    logger.info(f"Uploaded file: {os.path.basename(file_path)}")
                logger.info("Files synced to the database.")
        except Exception as e:
            logger.exception(f"Failed to upload files to DB: {e}")

    def sync_to_database(self, archive_dir):
        self.archive_files(archive_dir)
        self.upload_to_database()

    def get_file_count(self):
        return len([f for f in self.files if not f.endswith('_metadata.json') and not f.endswith('.json')])


# -----------------------------------------------------------
# File Processor
# -----------------------------------------------------------

class FileProcessor:
    def __init__(self, device_ID, rename_folder, processed_dir, exceptions_dir, input_pattern, gui_manager, session_manager):
        self.device_ID = device_ID
        self.rename_folder = rename_folder
        self.processed_dir = processed_dir
        self.exceptions_dir = exceptions_dir
        self.input_pattern = input_pattern
        self.gui_manager = gui_manager
        self.session_manager = session_manager
        self.data_type = ''
        self.daily_counter = 1
        self.records_dict = {}

    def reset_daily_counter(self):
        self.daily_counter = 1

    def generate_rename_filename(self, original_filename):
        _, extension = os.path.splitext(original_filename)
        date_str = datetime.datetime.now().strftime('%Y%m%d')
        new_filename = f"{self.device_ID}_rename-file_{date_str}{extension}"
        new_path = os.path.join(self.rename_folder, new_filename)
        return get_unique_path(new_path)

    def update_records(self, record_name, record_ID, path, in_db=False):
        if record_ID not in self.records_dict:
            record_ID += f'-{self.daily_counter}'
            self.daily_counter += 1
            self.records_dict[record_ID] = LocalRecord(record_name, record_ID, in_db)
        self.records_dict[record_ID].add_item(path)

    def manage_session(self):
        if not self.session_manager.session_active:
            self.session_manager.start_session()
            self.gui_manager.show_done_dialog(self.session_manager.end_session_callback)
        else:
            self.session_manager.reset_timer()

    def validate_user_input(self, dialog_result):
        if dialog_result is None:
            logger.info("User cancelled dialog.")
            return False, "User cancelled the dialog."
        user_ID = dialog_result['name']
        institute = dialog_result['institute']
        sample_ID = dialog_result['sample_ID']
        if not user_ID or not institute or not sample_ID:
            return False, "All fields are required."
        return True, (user_ID, institute, sample_ID)

    def record_in_archive(self, record_name, archive_json):
        if os.path.exists(archive_json):
            with open(archive_json, 'r') as file:
                archived_records = json.load(file)
            return record_name in archived_records
        return False

    def get_record_dict_for_sync(self):
        return self.records_dict

    def clear_records_dict(self):
        self.records_dict.clear()

    def process_incoming_file_or_folder(self, path):
        if os.path.isfile(path):
            self.process_file(path)
        elif os.path.isdir(path):
            self.process_folder(path)

    def process_file(self, file_path):
        filename = os.path.basename(file_path)
        base_name, extension = os.path.splitext(filename)

        # Check if TIFF
        if not is_tiff_file(filename):
            logger.info(f"'{filename}' is not a TIFF file.")
            self.move_to_exceptions(file_path)
            return

        if is_valid_filename(base_name):
            # Valid name, rename properly
            self.finalize_rename(file_path, base_name, extension, is_folder=False)
        else:
            logger.info(f"'{filename}' does not match naming convention.")
            self.prompt_rename(file_path, filename, is_folder=False)

    def process_folder(self, folder_path):
        folder_name = os.path.basename(folder_path)
        # ELID folder check
        if not self.is_elid_folder(folder_path):
            logger.info(f"Folder '{folder_name}' does not contain an .elid file.")
            self.move_to_exceptions(folder_path, is_folder=True)
            return

        if is_valid_filename(folder_name):
            self.finalize_rename(folder_path, folder_name, "", is_folder=True)
        else:
            logger.info(f"Folder '{folder_name}' does not match naming convention.")
            self.prompt_rename(folder_path, folder_name, is_folder=True)

    def is_elid_folder(self, folder_path):
        if os.path.isdir(folder_path):
            for file in os.listdir(folder_path):
                if file.endswith('.elid'):
                    self.data_type = 'elid'
                    return True
        return False

    def finalize_rename(self, path, base_name, extension="", is_folder=False, notify=True):
        # Construct new name and get unique path
        record_name, record_ID, new_path = self.construct_names_and_id(base_name, extension)
        try:
            move_item(path, new_path)
            if notify:
                self.gui_manager.show_info("Success", f"{'Folder' if is_folder else 'File'} renamed to '{os.path.basename(new_path)}'")
            # Check if already archived
            if self.record_in_archive(record_name, ARCHIVED_FILES_JSON):
                if self.gui_manager.prompt_append_record(record_name):
                    self.update_records(record_name, record_ID, new_path)
                    self.manage_session()
                else:
                    self.prompt_rename(path, os.path.basename(path), existing_record=True, is_folder=is_folder)
            else:
                self.update_records(record_name, record_ID, new_path)
                self.manage_session()
        except Exception:
            self.move_to_rename_folder(path, os.path.basename(path), is_folder=is_folder)

    def construct_names_and_id(self, base_name, extension):
        base_name = scrub_input(base_name)
        # Expecting base_name format: Institute_UserName_Sample
        # Append date and possibly device and type
        # Original code suggests: Institute_UserName_SampleName_Date
        # This might need alignment with the original specification.
        parts = base_name.split('_')
        # If original format doesn't have date, add it:
        date_str = datetime.datetime.now().strftime('%Y%m%d')
        if len(parts) == 3:
            institute, user_ID, sample_ID = parts
            base_name = f"{institute}_{user_ID}_{sample_ID}_{date_str}"
        else:
            # If user corrected naming or original had 4 parts including date:
            # Assume last segment is date
            institute, user_ID, sample_ID, date_str = parts[:4]

        record_name = sample_ID
        record_ID = f"{self.device_ID}-{date_str}-{self.data_type}-{institute}-{user_ID}"
        new_path = get_unique_path(os.path.join(self.processed_dir, base_name + extension))
        return record_name, record_ID, new_path

    def prompt_rename(self, path, name, existing_record=False, is_folder=False):
        if existing_record:
            msg = f"Rename '{name}' to create new record."
            self.gui_manager.show_info("Rename for New Record", msg)
        else:
            msg = (f"The {'folder' if is_folder else 'file'} '{name}' does not adhere to naming convention.\n"
                   f"Format: Institute_UserName_Sample-Name (e.g., IPAT_MuS_Sample-Name)")
            self.gui_manager.show_warning("Invalid Name", msg)

        extension = os.path.splitext(name)[1] if not is_folder else ""
        while True:
            dialog_result = self.gui_manager.prompt_rename()
            is_valid, result = self.validate_user_input(dialog_result)
            if not is_valid:
                if result == "User cancelled the dialog.":
                    self.move_to_rename_folder(path, name, is_folder=is_folder)
                    return
                else:
                    self.gui_manager.show_warning("Incomplete Information", result)
                    continue
            user_ID, institute, sample_ID = result
            date_str = datetime.datetime.now().strftime('%Y%m%d')
            base_name = f"{institute}_{user_ID}_{sample_ID}_{date_str}"
            self.finalize_rename(path, base_name, extension, is_folder=is_folder, notify=True)
            break

    def move_to_rename_folder(self, path, name, is_folder=False):
        new_path = self.generate_rename_filename(name)
        try:
            move_item(path, new_path)
            self.gui_manager.show_info(
                "Moved",
                f"Renaming was cancelled or failed. The {'folder' if is_folder else 'file'} "
                f"has been moved to: {new_path}"
            )
        except Exception as e:
            self.gui_manager.show_error("Error", f"Failed to move {'folder' if is_folder else 'file'}: {e}")

    def move_to_exceptions(self, path, is_folder=False):
        new_path = os.path.join(self.exceptions_dir, os.path.basename(path))
        try:
            move_item(path, new_path)
        except Exception as e:
            self.gui_manager.show_error("Error", f"Failed to move to exceptions: {e}")


# -----------------------------------------------------------
# Watchdog Event Handler
# -----------------------------------------------------------

class FileEventHandler(FileSystemEventHandler):
    def __init__(self, event_queue):
        super().__init__()
        self.event_queue = event_queue

    def on_created(self, event):
        self.event_queue.put(event.src_path)
        logger.info(f"New file detected: {event.src_path}")


# -----------------------------------------------------------
# Main Application
# -----------------------------------------------------------

class DeviceWatchdogApp:
    def __init__(self,
                 watch_dir,
                 device_name,
                 rename_folder,
                 processed_dir,
                 archive_dir,
                 exceptions_dir,
                 test_path,
                 session_timeout=60,
                 testing=False):
        self.testing = testing
        self.test_path = test_path
        self.watch_dir = watch_dir
        self.staging_dir = processed_dir
        self.archive_dir = archive_dir
        if testing:
            for root, dirs, files in os.walk(watch_dir):
                for file in files:
                    os.remove(os.path.join(root, file))
                for dir in dirs:
                    shutil.rmtree(os.path.join(root, dir))

        self.session_timeout = session_timeout
        self.gui_manager = GUIManager()
        self.session_manager = SessionManager(session_timeout, self.end_session, self.gui_manager.root)

        # Ensure directories
        os.makedirs(rename_folder, exist_ok=True)
        os.makedirs(processed_dir, exist_ok=True)
        os.makedirs(archive_dir, exist_ok=True)
        os.makedirs(exceptions_dir, exist_ok=True)

        self.processed_files = {}
        self.file_processor = FileProcessor(
            device_ID=device_name,
            rename_folder=rename_folder,
            processed_dir=processed_dir,
            exceptions_dir=exceptions_dir,
            input_pattern=FILENAME_PATTERN,
            gui_manager=self.gui_manager,
            session_manager=self.session_manager
        )

        self.event_queue = queue.Queue()
        self.session_event = threading.Event()
        self.session_active = False
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
        self.gui_manager.show_error(
            "Application Error",
            "An unexpected error occurred. Please contact the administrator."
        )
        self.on_closing()

    def end_session(self):
        try:
            self.session_active = False
            if self.session_timer:
                self.session_timer.cancel()
            logger.info("Session ended.")
            self.sync_files_to_database()
        except Exception as e:
            logger.exception(f"Error during session end: {e}")
            self.gui_manager.show_error("Session End Error", str(e))
        finally:
            if hasattr(self.gui_manager, 'done_dialog') and self.gui_manager.done_dialog.winfo_exists():
                self.gui_manager.done_dialog.destroy()

    def sync_files_to_database(self):
        logger.info("Syncing files to the database...")
        records_dict = self.file_processor.get_record_dict_for_sync()
        for local_record in records_dict.values():
            local_record.sync_to_database(self.archive_dir)
            num_files = local_record.get_file_count()
            self.processed_files[local_record.record_id] = self.processed_files.get(local_record.record_id, 0) + num_files
            logger.info(f"Updated count for record '{local_record.record_id}': {self.processed_files[local_record.record_id]} files.")
        self.file_processor.clear_records_dict()
        self.update_archived_files_list()

    def update_archived_files_list(self):
        try:
            with open(ARCHIVED_FILES_JSON, 'w') as f:
                json.dump(self.processed_files, f, indent=4)
            logger.info("Processed files data saved.")
        except Exception as e:
            logger.exception(f"Failed to save processed files data: {e}")

    def process_events(self):
        while not self.event_queue.empty():
            data_path = self.event_queue.get()
            self.file_processor.process_incoming_file_or_folder(data_path)
        self.gui_manager.root.after(100, self.process_events)

        # Testing hook
        if self.testing:
            if os.path.isfile(self.test_path):
                shutil.copy(self.test_path, self.watch_dir)
            elif os.path.isdir(self.test_path):
                shutil.copytree(self.test_path, os.path.join(self.watch_dir, os.path.basename(self.test_path)))
            self.testing = False

        if datetime.datetime.now().hour == 0:
            self.file_processor.reset_daily_counter()

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
    testing = True
    test_path = r"D:\Repos\ipat_data_watchdog\test_elid"
    logger.info("Starting Device Watchdog application...")
    app = DeviceWatchdogApp(
        watch_dir=WATCH_DIR,
        device_name=DEVICE_NAME,
        rename_folder=RENAME_DIR,
        processed_dir=STAGING_DIR,
        archive_dir=ARCHIVE_DIR,
        exceptions_dir=EXCEPTIONS_DIR,
        test_path=test_path,
        session_timeout=SESSION_TIMEOUT_SECONDS,
        testing=testing,
    )
    try:
        app.run()
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
    finally:
        logger.info("Application closed.")
