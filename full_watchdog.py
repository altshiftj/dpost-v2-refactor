import os
import re
import sys
import json
import queue
import logging
import time
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

DEVICE_NAME = "REM_001"

WATCH_DIR = r"test_monitor"
RENAME_DIR = os.path.join(WATCH_DIR, 'To_Rename')
STAGING_DIR = os.path.join(WATCH_DIR, 'Staging')
ARCHIVE_DIR = os.path.join(WATCH_DIR, 'Archive')
EXCEPTIONS_DIR = os.path.join(WATCH_DIR, 'Exceptions')
ARCHIVED_FILES_JSON = os.path.join(ARCHIVE_DIR, 'processed_files.json')

FILENAME_PATTERN = re.compile(r'^[A-Za-z0-9]+_[A-Za-z0-9]+_[A-Za-z0-9]+$')

logging.basicConfig(filename='watchdog.log', level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


class FileEventHandler(FileSystemEventHandler):
    """
    Event handler that processes new files.
    """
    def __init__(self, event_queue):
        super().__init__()
        self.event_queue = event_queue

    def on_created(self, event):
        self.event_queue.put(event.src_path)
        logger.info(f"New file detected: {event.src_path}")


class SessionManager:
    def __init__(self, session_timeout, end_session_callback, root: tk.Tk):
        self.session_timeout = session_timeout * 1000  # milliseconds
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
        if not self.session_active:
            logger.warning("SessionManager.end_session called but session already ended. Skipping.")
            return
        self.session_active = False
        if self.session_timer_id is not None:
            self.root.after_cancel(self.session_timer_id)
            self.session_timer_id = None
        logger.info("Session ended.")
        # Call the callback exactly once
        self.end_session_callback()

    def cancel(self):
        if self.session_timer_id is not None:
            self.root.after_cancel(self.session_timer_id)
            self.session_timer_id = None


class GUIManager:
    """
    Manages all GUI-related interactions using Tkinter.
    """
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
        return messagebox.askyesno("Append to Existing Record", f"Record '{record_name}' has been previously synced. Add file to existing record?", parent=self.dialog_parent)

    def show_done_dialog(self, session_manager: SessionManager):
        if hasattr(self, 'done_dialog') and self.done_dialog.winfo_exists():
            self.done_dialog.destroy()

        self.done_dialog = tk.Toplevel(self.root)
        self.done_dialog.title("Session Active")
        self.done_dialog.attributes("-topmost", True)

        label = tk.Label(self.done_dialog, text="A session is in progress. Click 'Done' when finished.")
        label.pack(padx=20, pady=10)

        done_button = tk.Button(self.done_dialog, text="Done", command=self._end_session_via_manager(session_manager))
        done_button.pack(pady=10)

        self.done_dialog.protocol("WM_DELETE_WINDOW", self._close_dialog)

    def _end_session_via_manager(self, session_manager: SessionManager):
        def wrapper():
            if self.done_dialog and self.done_dialog.winfo_exists():
                self.done_dialog.destroy()
            session_manager.end_session()
        return wrapper

    def _close_dialog(self):
        if self.done_dialog and self.done_dialog.winfo_exists():
            self.done_dialog.destroy()

    def destroy(self):
        self.dialog_parent.destroy()
        self.root.destroy()


class EntryWithPlaceholder(tk.Entry):
    """
    Entry with placeholder text.
    """
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
    """
    Dialog to collect Name, Institute, and Sample Name.
    """
    def __init__(self, parent, title=None):
        super().__init__(parent, title)

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

        master.grid_columnconfigure(0, weight=0)
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

        if userID == self.example_user_ID:
            userID = ""
        if institute == self.example_institute:
            institute = ""
        if sample_ID == self.example_sample_ID:
            sample_ID = ""

        self.result = {
            'name': userID,
            'institute': institute,
            'sample_ID': sample_ID,
        }


class LocalRecord:
    """
    Represents a collection of files for a single record.
    """
    def __init__(self, record_name, record_id, in_db=False):
        self.record_name = record_name
        self.record_id = record_id
        self.in_db = in_db
        self.files = []
        self.metadata = {}

    def add_item(self, path: str):
        if os.path.isfile(path):
            self.files.append(path)
        elif os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for file in files:
                    file_path = os.path.join(root, file)
                    self.files.append(file_path)
        else:
            logger.warning(f"Path '{path}' is neither a file nor a directory.")

    def get_file_count(self):
        return len([f for f in self.files if not f.endswith('_metadata.json') and not f.endswith('.json')])

    def upload_to_database(self):
        try:
            with KadiManager() as db_manager:
                if self.in_db:
                    metadata_staging_path = os.path.join(STAGING_DIR, f"{self.record_name}_metadata.json")
                    kadi_record = db_manager.record(identifier=self.record_name)
                    file_id = kadi_record.get_file_id(file_name=f"{self.record_name}_metadata.json")
                    kadi_record.download_file(file_id=file_id, file_path=metadata_staging_path)

                    with open(metadata_staging_path, 'r') as file:
                        db_metadata = json.load(file)

                    db_metadata.update(self.metadata)

                    with open(metadata_staging_path, 'w') as file:
                        json.dump(db_metadata, file, indent=4)

                    kadi_record.upload_file(metadata_staging_path)

                    for file_path in self.files:
                        if not kadi_record.has_file(os.path.basename(file_path)):
                            kadi_record.upload_file(file_path)
                            logger.info(f"Uploaded file: {os.path.basename(file_path)}")
                else:
                    kadi_record = db_manager.record(create=True, identifier=self.record_id)
                    kadi_record.set_attribute('title', self.record_name)
                    for file_path in self.files:
                        kadi_record.upload_file(file_path)
                        logger.info(f"Uploaded file: {os.path.basename(file_path)}")

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


class FileProcessor:
    """
    Handles file validation, renaming, moving, and archiving.
    """
    def __init__(self, device_ID, rename_folder, staging_dir, archive_dir, exceptions_dir, input_pattern, gui_manager: GUIManager, session_manager: SessionManager):
        self.device_ID = device_ID
        self.rename_folder = rename_folder
        self.staging_dir = staging_dir
        self.archive_dir = archive_dir
        self.exceptions_dir = exceptions_dir
        self.input_pattern = input_pattern
        self.gui_manager = gui_manager
        self.session_manager = session_manager

        self.data_type = ''
        self.daily_counter = 0
        self.records_dict = {}
        self.archived_files_json = os.path.join(self.archive_dir, 'processed_files.json')
        self.processed_files = self.load_processed_files_data()

    def load_processed_files_data(self):
        if os.path.exists(self.archived_files_json):
            try:
                with open(self.archived_files_json, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.exception(f"Failed to load processed files data: {e}")
                return {}
        else:
            return {}

    def save_processed_files_data(self):
        try:
            with open(self.archived_files_json, 'w') as f:
                json.dump(self.processed_files, f, indent=4)
            logger.info("Processed files data saved.")
        except Exception as e:
            logger.exception(f"Failed to save processed files data: {e}")

    def update_archived_record(self, record_id, file_count):
        self.processed_files[record_id] = self.processed_files.get(record_id, 0) + file_count
        logger.info(f"Updated count for record '{record_id}': {self.processed_files[record_id]} files.")
        self.save_processed_files_data()

    def is_tiff_file(self, filename):
        self.data_type = 'img'
        return filename.lower().endswith(('.tiff', '.tif'))
    
    def is_elid_folder(self, folder_path):
        if os.path.isdir(folder_path):
            for file in os.listdir(folder_path):
                if file.endswith('.elid'):
                    self.data_type = 'elid'
                    return True
        return False

    def is_valid_name(self, base_name):
        return self.input_pattern.match(base_name) is not None

    def scrub_input(self, input_str):
        return re.sub(r'[^A-Za-z0-9_-]+', '_', input_str)

    def reset_daily_counter(self):
        self.daily_counter = 1

    def get_unique_path(self, dest_path):
        directory, filename = os.path.split(dest_path)
        base, extension = os.path.splitext(filename)
        counter = 1
        unique_filename = f"{base}_{counter}{extension}"
        while os.path.exists(os.path.join(directory, unique_filename)):
            counter += 1
            unique_filename = f"{base}_{counter}{extension}"
        return os.path.join(directory, unique_filename)

    def generate_rename_filename(self, original_filename):
        _, extension = os.path.splitext(original_filename)
        date_str = datetime.datetime.now().strftime('%Y%m%d')
        new_filename = f"{self.device_ID}_rename-file_{date_str}{extension}"
        new_path = os.path.join(self.rename_folder, new_filename)
        unique_new_path = self.get_unique_path(new_path)
        return unique_new_path

    def update_record(self, base_name, record_ID, path, in_db=False):
        if base_name not in self.records_dict:
            parts = record_ID.split('-')
            self.daily_counter += 1
            parts.insert(2, f'REC_{self.daily_counter:03}')
            record_ID = '-'.join(parts)
            self.records_dict[base_name] = LocalRecord(base_name, record_ID, in_db)
        self.records_dict[base_name].add_item(path)

    def manage_session(self):
        if not self.session_manager.session_active:
            self.session_manager.start_session()
            self.gui_manager.show_done_dialog(self.session_manager)
        else:
            self.session_manager.reset_timer()

    def validate_user_input(self, dialog_result):
        if dialog_result is None:
            logger.info("User cancelled the dialog.")
            return False, "User cancelled the dialog."

        user_ID = dialog_result['name']
        institute = dialog_result['institute']
        sample_ID = dialog_result['sample_ID']

        if not user_ID or not institute or not sample_ID:
            return False, "All fields are required. Please fill in all fields."
        return True, (user_ID, institute, sample_ID)
    
    def record_in_archive(self, record_name, archive_json):
        if os.path.exists(archive_json):
            with open(archive_json, 'r') as file:
                archived_records = json.load(file)
            if record_name in archived_records:
                return True
        return False
    
    def get_record_dict_for_sync(self):
        return self.records_dict
    
    def clear_records_dict(self):
        self.records_dict.clear()

    def clear_staging_dir(self):
        for root, dirs, files in os.walk(self.staging_dir):
            for file in files:
                os.remove(os.path.join(root, file))
            for dir in dirs:
                shutil.rmtree(os.path.join(root, dir))

    def process_incoming_file_or_folder(self, path):
        if os.path.isfile(path):
            self.process_tiff_file(path)
        elif os.path.isdir(path):
            self.process_elid_folder(path)

    def process_tiff_file(self, file_path):
        """
        Processes a TIFF file, validating and renaming as necessary.
        Automatically appends the device name and date if not included.
        """
        filename = os.path.basename(file_path)
        base_name, extension = os.path.splitext(filename)

        if not self.is_tiff_file(filename):
            logger.info(f"File '{filename}' is not a TIFF file.")
            new_path = os.path.join(self.exceptions_dir, filename)
            try:
                os.rename(file_path, new_path)
                logger.info(f"File moved from '{file_path}' to '{new_path}'.")
            except Exception as e:
                logger.exception(f"Failed to move file '{file_path}' to '{new_path}': {e}")
            return

        # Automatically handle files named with the simplified convention
        if self.is_valid_name(base_name) or len(base_name.split('_')) == 3:
            self.rename_item(file_path, base_name, extension, is_folder=False, notify=False)
        else:
            logger.info(f"File '{filename}' does not match the naming convention.")
            self.prompt_rename(file_path, filename, is_folder=False)

    def process_elid_folder(self, folder_path):
        """
        Processes a folder, validating and renaming as necessary.
        Automatically appends the device name and date if not included.
        """
        folder_name = os.path.basename(folder_path)
        if not self.is_elid_folder(folder_path):
            logger.info(f"Folder '{folder_name}' does not contain an .elid file.")
            new_path = os.path.join(self.exceptions_dir, folder_name)
            try:
                os.rename(folder_path, new_path)
                logger.info(f"Folder moved from '{folder_path}' to '{new_path}'.")
            except Exception as e:
                logger.exception(f"Failed to move folder '{folder_path}' to '{new_path}': {e}")
            return

        # Automatically handle folders named with the simplified convention
        if self.is_valid_name(folder_name) or len(folder_name.split('_')) == 3:
            self.rename_item(folder_path, folder_name, is_folder=True, notify=False)
        else:
            logger.info(f"Folder '{folder_name}' does not match the naming convention.")
            self.prompt_rename(folder_path, folder_name, is_folder=True)

    def construct_names_and_id(self, base_name, extension):
        """
        Constructs record name, record ID, and unique file path.
        Automatically appends device name and date if necessary.
        """
        base_name = self.scrub_input(base_name)

        # Check if base_name matches the simpler convention (INST_USER_SAMPLE)
        parts = base_name.split('_')
        if len(parts) == 3:
            institute, user_ID, sample_ID = parts
            date = datetime.datetime.now().strftime('%Y%m%d')  # Use current date
            base_name = f"{institute}_{user_ID}_{sample_ID}_{date}"  # Append date
        elif len(parts) == 4:
            institute, user_ID, sample_ID, date = parts
        else:
            raise ValueError("Invalid base name format for constructing names and ID.")

        record_name = sample_ID
        record_ID = f"{self.device_ID}-{date}-{self.data_type}-{institute}-{user_ID}"
        new_path = os.path.join(self.staging_dir, base_name + extension)
        unique_new_path = self.get_unique_path(new_path)
        return base_name, record_ID, unique_new_path

    def rename_item(self, path, base_name, extension="", is_folder=False, notify=True):
        base_name, record_ID, new_path = self.construct_names_and_id(base_name, extension)
        try:
            os.rename(path, new_path)
            if is_folder and self.data_type == 'elid':
                for file in os.listdir(new_path):
                    if file.endswith('.elid') or file.endswith('.odt'):
                        old_file_path = os.path.join(new_path, file)
                        _, file_ext = os.path.splitext(file)
                        new_file_name = base_name + file_ext
                        new_file_path = os.path.join(new_path, new_file_name)
                        os.rename(old_file_path, new_file_path)

            if notify:
                self.gui_manager.show_info("Success", f"{'Folder' if is_folder else 'File'} renamed to '{os.path.basename(new_path)}'")
            logger.info(f"{'Folder' if is_folder else 'File'} '{path}' renamed to '{new_path}'.")

            if self.record_in_archive(base_name, ARCHIVED_FILES_JSON):
                if self.gui_manager.prompt_append_record(base_name):
                    self.update_record(base_name, record_ID, new_path)
                    self.manage_session()
                else:
                    self.prompt_rename(path, os.path.basename(path), existing_record=True, is_folder=is_folder)
            else:
                self.update_record(base_name, record_ID, new_path)
                self.manage_session()

        except Exception as e:
            self.gui_manager.show_error("Error", f"Failed to rename {'folder' if is_folder else 'file'}: {e}")
            logger.exception(f"Failed to rename {'folder' if is_folder else 'file'} '{path}' to '{new_path}': {e}")
            self.move_to_rename_folder(path, os.path.basename(path), is_folder=is_folder)

    def prompt_rename(self, path, name, existing_record=False, is_folder=False):
        if existing_record:
            message = f"Rename '{name}' to create new record.\n"
            self.gui_manager.show_info("Rename for New Record", message)
        else:
            message = (
                f"The {'folder' if is_folder else 'file'} '{name}' does not adhere to the naming convention.\n"
                f"The required naming format is: Institute_UserName_Sample-Name (e.g., IPAT_MuS_Sample-Name)"
            )
            self.gui_manager.show_warning("Invalid Name", message)

        extension = os.path.splitext(name)[1] if not is_folder else ""

        while True:
            dialog_result = self.gui_manager.prompt_rename()
            is_valid, result = self.validate_user_input(dialog_result)
            if not is_valid:
                if result == "User cancelled the dialog.":
                    logger.info("User cancelled the dialog.")
                    self.move_to_rename_folder(path, name, is_folder=is_folder)
                    return
                else:
                    self.gui_manager.show_warning("Incomplete Information", result)
                    continue

            user_ID, institute, sample_ID = result
            date_str = datetime.datetime.now().strftime('%Y%m%d')
            base_name = f"{institute}_{user_ID}_{sample_ID}_{date_str}"
            self.rename_item(path, base_name, extension, is_folder=is_folder, notify=True)
            break

    def move_to_rename_folder(self, path, name, is_folder=False):
        new_path = self.generate_rename_filename(name)
        try:
            os.rename(path, new_path)
            self.gui_manager.show_info("Moved", f"Renaming was cancelled or failed. The {'folder' if is_folder else 'file'} has been moved to: {new_path}")
            logger.info(f"{'Folder' if is_folder else 'File'} moved from '{path}' to '{new_path}'.")
        except Exception as e:
            self.gui_manager.show_error("Error", f"Failed to move {'folder' if is_folder else 'file'}: {e}")
            logger.exception(f"Failed to move {'folder' if is_folder else 'file'} '{path}' to '{new_path}': {e}")

    def archive_record_files(self, record: LocalRecord):
        record_dir = os.path.join(self.archive_dir, record.record_id)
        if not os.path.exists(record_dir):
            os.mkdir(record_dir)

        for file_path in record.files:
            basename = os.path.basename(file_path)
            dirname = os.path.split(os.path.dirname(file_path))[-1]

            if 'analysis' in dirname and not 'analysis' in basename:
                new_basename = f'{dirname}_{basename}'
                dest_path = os.path.join(record_dir, new_basename)
            else:
                dest_path = os.path.join(record_dir, basename)

            try:
                os.rename(file_path, dest_path)
                record.files[record.files.index(file_path)] = dest_path
                logger.info(f"Archived file '{file_path}' to '{dest_path}'.")
            except Exception as e:
                logger.exception(f"Failed to move file '{file_path}' to '{dest_path}': {e}")


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
            self.file_processor.archive_record_files(local_record)
            self.file_processor.update_archived_record(local_record.record_id, local_record.get_file_count())
            local_record.upload_to_database()

        self.file_processor.clear_records_dict()
        self.file_processor.clear_staging_dir()

    def process_events(self):
        while not self.event_queue.empty():

            # wait for file/folder to be fully written
            time.sleep(0.5)

            data_path = self.event_queue.get()
            self.file_processor.process_incoming_file_or_folder(data_path)
        self.gui_manager.root.after(100, self.process_events)

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
