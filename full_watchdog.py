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

# TODO: Consider Clocks, Synchronization of Data Time

DEVICE_NAME = "SEM"

WATCH_DIR = r"test_monitor"
RENAME_DIR = os.path.join(WATCH_DIR, 'To_Rename')
STAGING_DIR = os.path.join(WATCH_DIR, 'Staging')
ARCHIVE_DIR = os.path.join(WATCH_DIR, 'Archive')
EXCEPTIONS_DIR = os.path.join(WATCH_DIR, 'Exceptions') # TODO: Implement exceptions folder in file handling
ARCHIVED_FILES_JSON = os.path.join(ARCHIVE_DIR, 'processed_files.json')

FILENAME_PATTERN = re.compile(r'^[A-Za-z0-9]+_[A-Za-z0-9]+_[A-Za-z0-9]+$')

# Configure logging
logging.basicConfig(filename='watchdog.log', level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# FileEventHandler deals with new files as they arrive, and places them in the event queue for processing
class FileEventHandler(FileSystemEventHandler):
    """
    Event handler that processes new files.
    """
    def __init__(self, event_queue):
        super().__init__()
        self.event_queue = event_queue

    def on_created(self, event):
        # Add a newly added file path to the queue
        self.event_queue.put(event.src_path)
        logger.info(f"New file detected: {event.src_path}")

# SessionManager deals with session starts, ends, and timing out
class SessionManager:
    def __init__(self, session_timeout, end_session_callback, root: tk.Tk):
        self.session_timeout = session_timeout * 1000  # Convert seconds to milliseconds
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
        # Call the callback to perform syncing
        self.end_session_callback()

    def cancel(self):
        if self.session_timer_id is not None:
            self.root.after_cancel(self.session_timer_id)
            self.session_timer_id = None

# GuiManager manages all GUI-related interactions using Tkinter
class GUIManager:
    """
    Manages all GUI-related interactions using Tkinter.
    """
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()  # Hide the root window

        # Create a dialog parent window
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

    def show_done_dialog(self, end_session_callback):
        self.done_dialog = tk.Toplevel(self.root)
        self.done_dialog.title("Session Active")
        self.done_dialog.attributes("-topmost", True)
        label = tk.Label(self.done_dialog, text="A session is in progress. Click 'Done' when finished.")
        label.pack(padx=20, pady=10)
        done_button = tk.Button(self.done_dialog, text="Done", command=end_session_callback)
        done_button.pack(pady=10)
        # Handle dialog close event
        self.done_dialog.protocol("WM_DELETE_WINDOW", lambda: None)  # Do nothing on close

    def destroy(self):
        self.dialog_parent.destroy()
        self.root.destroy()

# Custom Entry widget with placeholder text
class EntryWithPlaceholder(tk.Entry):
    """
    Custom Entry widget with placeholder text. This fills the rename dialog fields with placeholder name, institute, and sample name.
    """
    def __init__(self, master=None, placeholder="PLACEHOLDER", color='grey', *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.placeholder = placeholder
        self.placeholder_color = color
        self.default_fg_color = self['fg']

        self.bind("<FocusOut>", self._focus_out)
        self.bind("<Key>", self._key_pressed)  # Bind to key press event

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
        # Hide placeholder on key press
        if self['fg'] == self.placeholder_color:
            self.delete(0, 'end')
            self['fg'] = self.default_fg_color

    def _focus_out(self, event):
        # Show placeholder if entry is empty
        if not super().get():
            self._show_placeholder()

    def get(self):
        # Override get method to return empty string if placeholder is visible
        content = super().get()
        if self['fg'] == self.placeholder_color:
            return ''
        else:
            return content

# Custom dialog using EntryWithPlaceholder to collect Name, Institute, and Sample Name from users when a file name is incorrect
class MultiFieldDialog(simpledialog.Dialog):
    """
    Custom dialog to collect Name, Institute, and Sample Name.
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

        # Use EntryWithPlaceholder to fill the fields with placeholder text
        self.name_entry = EntryWithPlaceholder(master, self.example_user_ID, textvariable=self.user_ID_var)
        self.institute_entry = EntryWithPlaceholder(master, self.example_institute, textvariable=self.institute_var)
        self.data_qualifier_entry = EntryWithPlaceholder(master, self.example_sample_ID, textvariable=self.sample_ID_var)
        # define the grid layout of the rename dialog
        self.name_entry.grid(row=0, column=1, sticky='we', padx=5, pady=2)
        self.institute_entry.grid(row=1, column=1, sticky='we', padx=5, pady=2)
        self.data_qualifier_entry.grid(row=2, column=1, sticky='we', padx=5, pady=2)

        # Configure column weights
        master.grid_columnconfigure(0, weight=0)
        master.grid_columnconfigure(1, weight=1)

        # Schedule lift and topmost attributes to be set after window is created
        self.after(0, self._bring_to_front)

        return self.name_entry  # initial focus

    def _bring_to_front(self):
        self.lift()
        self.wm_attributes("-topmost", True)

    def apply(self):
        # Ensure placeholders are not included in the result
        userID = self.user_ID_var.get()
        institute = self.institute_var.get()
        sample_ID = self.sample_ID_var.get()

        # Validate that the placeholders are not submitted
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

# LocalRecord represents a collection of files with the same root_name (cf record name) and their associated metadata
class LocalRecord:
    """
    Represents a collection of files with the same base_name.
    """
    def __init__(self, record_name, record_id, in_db=False):
        self.record_name = record_name
        self.record_id=record_id
        self.in_db = in_db
        self.files = []  # List of file paths
        metadata = {}

    def add_item(self, path: str):
        if os.path.isfile(path):
            self.files.append(path)
        elif os.path.isdir(path):
            # Add all files in the folder to self.files
            for root, dirs, files in os.walk(path):
                for file in files:
                    # FIXME: Difficulty in deciding record name/id/filenames
                    # Try to resolve in cases of renaming, staging, archiving, and syncing
                    rel_record_path = os.path.split(path)
                    file_path = os.path.join(self.record_id, file)
                    self.files.append(file_path)
        else:
            logger.warning(f"Path '{path}' is neither a file nor a directory.")

        # TODO: Extract metadata from the file and add it to the metadata dictionary

    def save_metadata_to_json(self, dest_folder):
        """
        Saves the aggregate metadata to a JSON file in the same directory as the file.
        """
        # define the metadata path (directory = filepath, filename is the record base_name + '_metadata.json' suffix)
        metadata_path = os.path.join(dest_folder, f"{self.record_name}_metadata.json")

        try:
            with open(metadata_path, 'w') as f:
                json.dump(self.metadata, f, indent=4)
                self.add_file(metadata_path)
            logger.info(f"Metadata saved to '{metadata_path}'")
        except Exception as e:
            logger.exception(f"Failed to save metadata to '{metadata_path}': {e}")

    def upload_to_database(self):
        """
        Uploads files to the database.
        """
        try:
            with KadiManager() as db_manager:
                if self.in_db:
                    metadata_staging_path = os.join(STAGING_DIR, f"{self.record_name}_metadata.json")
                    kadi_record = db_manager.record(identifier=self.record_name)
                    file_id = kadi_record.get_file_id(file_name=f"{self.record_name}_metadata.json")
                    kadi_record.download_file(file_id=file_id, file_path=metadata_staging_path)
                    with open(metadata_staging_path, 'r') as file:
                        db_metadata = json.load(file)
                    with open(db_metadata, 'w') as file:
                        json.dump(self.metadata, file, indent=4)
                    return
                

                kadi_record = db_manager.record(create=True, id=self.record_name, identifier=self.record_name)
                for file_path in self.files:
                    kadi_record.upload_file(file_path)
                    logger.info(f"Uploaded file: {os.path.basename(file_path)}")
        except Exception as e:
            logger.exception(f"Failed to upload files to the database: {e}")

    def archive_files(self, archive_dir):
        """
        Moves all files to the archive directory.
        """
        
        # TODO: Integrate ELIDs into metadata collection. Perhaps 
        #self.save_metadata_to_json(archive_dir)



        for file_path in self.files:
            record_dir = os.path.join(archive_dir, self.record_id)
            if not os.path.exists(record_dir):  
                os.mkdir(record_dir)
            dest_path = os.path.join(record_dir, os.path.basename(file_path))

            try:
                os.rename(file_path, dest_path)

                # change the file path in the local record to the new path
                self.files[self.files.index(file_path)] = dest_path
                logger.info(f"Archived file '{file_path}' to '{dest_path}'.")
            except Exception as e:
                logger.exception(f"Failed to move file '{file_path}' to '{dest_path}': {e}")
                # Optionally handle exceptions, e.g., move to exceptions folder

    def sync_to_database(self, archive_dir):
        """
        Archives files and uploads them to the database.
        """
        self.archive_files(archive_dir)
        self.upload_to_database()

    def get_file_count(self):
        """
        Returns the number of files (excluding metadata files).
        """
        return len([f for f in self.files if not f.endswith('_metadata.json') and not f.endswith('.json')])

# MetadataExtractor contains extraction methods for metadata from TIFF files, etc.
class MetadataExtractor:
    """
    Class to handle metadata extraction from TIFF files.
    """

    @staticmethod
    def hash_file(file_path, chunk_size=65536):
        """
        Generates a hash for the file at the specified path.
        """
        try:
            hasher = hashlib.sha256()
            with open(file_path, 'rb') as file:
                while True:
                    data = file.read(chunk_size)  # 64 KB chunks
                    if not data:
                        break
                    hasher.update(data)
            return hasher.hexdigest()
        except Exception as e:
            logger.exception(f"Failed to hash file {file_path}: {e}")
            return None

    @staticmethod
    def flatten_xml_dict(d, parent_key='', sep='_'):
        """
        Recursively flattens a nested dictionary, handling XML attributes and units.
        """
        items = {}

        # if parent key contains FEI_Image, remove it
        if parent_key.startswith('FeiImage'):
            parent_key = parent_key.replace('FeiImage', '')

        for k, v in d.items():

            # Check if the key is an XML attribute or element
            if k.startswith('@'):
                # Attribute
                attr_name = k[1:]  # Remove '@'
                new_key = f"{parent_key}{sep}{attr_name}" if parent_key else attr_name
                items[new_key] = v
            
            # Check if the key is a unit
            elif k == '#text':
                # Text content
                if v.strip():
                    new_key = parent_key if parent_key else 'text'
                    items[new_key] = v.strip()
            else:
                # Element
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
                    # Leaf node
                    new_key = new_parent_key
                    items[new_key] = v
        return items
    
    @staticmethod
    def parse_xml_metadata(xml_string):
        """
        Parses XML string and returns a flat dictionary using xmltodict.
        """
        try:
            # Parse the XML string to a dictionary
            xml_dict = xmltodict.parse(xml_string)
            # Flatten the dictionary
            flat_dict = MetadataExtractor.flatten_xml_dict(xml_dict)
            return flat_dict
        except Exception as e:
            logger.exception(f"Failed to parse XML metadata: {e}")
            return {}

    @staticmethod
    def extract_tiff_metadata(file_path):
        """
        Extracts metadata from an SEM TIFF file and returns it as a flat dictionary.
        """
        base_name = os.path.basename(file_path)
        file_name, ext = os.path.splitext(base_name)
        file_hash = MetadataExtractor.hash_file(file_path)

        metadata = {}
        flattened_data = {}
        try:
            with tifffile.TiffFile(file_path) as tif:
                # Extract tags from the first page
                page = tif.pages[0]
                tags = page.tags

                # Process TIFF tags
                for tag in tags.values():
                    tag_name = tag.name
                    tag_value = tag.value

                    if isinstance(tag_value, tuple):
                        flattened_data = {f"{tag_name}_{i}": value for i, value in enumerate(tag_value)}

                    # Convert bytes to string if necessary
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

                    # Check if tag_name is 'FEI_TITAN' to parse embedded XML
                    if tag_name == "FEI_TITAN":
                        # Parse embedded XML
                        xml_metadata = MetadataExtractor.parse_xml_metadata(tag_value)

                        # convert any values that are number stored as strings to integers or floats
                        # and convert any 'None' values to string 'null'
                        for k, v in xml_metadata.items():
                            if v is None:
                                xml_metadata[k] = 'null'
                            elif re.match(r'^-?\d+$', v):  # Matches positive/negative integers
                                xml_metadata[k] = int(v)
                            elif re.match(r'^-?\d+(\.\d+)?$', v):  # Matches positive/negative floats
                                xml_metadata[k] = float(v)
                            elif re.match(r'^-?\d+(\.\d+)?[eE][-+]?\d+$', v):  # Matches scientific notation
                                xml_metadata[k] = float(v)

                        metadata.update(xml_metadata)

            # remove the extraneous key:value pairs from the metadata
            metadata.pop('FEI_TITAN', None)
            metadata.pop('xmlns:xsi', None)
            metadata.pop('xsi:noNamespaceSchemaLocation', None)

            # Add file hash to metadata
            metadata[f"filehash"] = file_hash

            # finally, append the filename to the keys in the metadata dictionary
            metadata = {f"{file_name}|{k}": v for k, v in metadata.items()}

        except Exception as e:
            logger.exception(f"Failed to extract metadata from {file_path}: {e}")
            return None
        return metadata


# FileProcessor handles file validation, renaming, and moving, and interacts with the GUIManager to alert the user of naming issues
# and interacts with the SessionManager to start sessions
class FileProcessor:
    """
    Handles file validation, renaming, and moving.
    """
    def __init__(self, device_ID, rename_folder, processed_dir, exceptions_dir, input_pattern, gui_manager: GUIManager, session_manager: SessionManager):
        self.device_ID = device_ID
        self.rename_folder = rename_folder
        self.processed_dir = processed_dir
        self.exceptions_dir = exceptions_dir
        self.input_pattern = input_pattern
        self.gui_manager = gui_manager
        self.session_manager = session_manager

        os.path.relpath

        self.daily_counter = 1

        self.records_dict = {}

    #region Utility Methods

    def is_tiff_file(self, filename):
        return filename.lower().endswith(('.tiff', '.tif'))
    
    def is_elid_folder(self, folder_path):
        # Check if it is a directory
        if os.path.isdir(folder_path):
            # Validate that the folder contains a file with the .elid extension
            for file in os.listdir(folder_path):
                if file.endswith('.elid'):
                    return True
        return False

    def is_valid_name(self, base_name):
        return self.input_pattern.match(base_name) is not None

    def scrub_input(self, input_str):
        """
        Scrubs the input string by replacing invalid characters for filenames with underscores.
        Allows letters, numbers, underscores, and hyphens.
        """
        return re.sub(r'[^A-Za-z0-9_-]+', '_', input_str)

    def reset_daily_counter(self):
        self.daily_counter = 0

    def get_unique_path(self, dest_path):
        """
        Generates a unique file path to avoid overwriting existing files.
        Always adds a counter to the filename to ensure uniqueness.
        """
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

    def update_records(self, record_name, record_ID, path, in_db=False):
        if record_ID not in self.records_dict:
            record_ID += f'-{self.daily_counter}'
            self.daily_counter += 1
            self.records_dict[record_ID] = LocalRecord(record_name, record_ID, in_db)
        self.records_dict[record_ID].add_item(path)

    def manage_session(self):
        if not self.session_manager.session_active:
            self.session_manager.start_session()
            # Show the session started dialog
            self.gui_manager.show_done_dialog(self.session_manager.end_session_callback)
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
        """
        Checks if the record has been archived before.
        """
        if os.path.exists(archive_json):
            with open(archive_json, 'r') as file:
                archived_records = json.load(file)
            if record_name in archived_records:
                return True
        else:
            return False
    
    def get_record_dict_for_sync(self):
        return self.records_dict
    
    def clear_records_dict(self):
        self.records_dict.clear()

    #endregion

    #region Main Methods

    def process_incoming_file_or_folder(self, path):
        if os.path.isfile(path):
            self.process_tiff_file(path)
        elif os.path.isdir(path):
            self.process_elid_folder(path)

    def process_tiff_file(self, file_path):
        filename = os.path.basename(file_path)
        base_name, extension = os.path.splitext(filename)
        
        if not self.is_tiff_file(filename):
            logger.info(f"File '{filename}' is not a TIFF file.")
            # move the file to the exceptions folder
            new_path = os.path.join(self.exceptions_dir, filename)
            try:
                os.rename(file_path, new_path)
                logger.info(f"File moved from '{file_path}' to '{new_path}'.")
            except Exception as e:
                logger.exception(f"Failed to move file '{file_path}' to '{new_path}': {e}")
            return

        if self.is_valid_name(base_name):
            # File meets the standard, rename accordingly
            self.rename_item(file_path, base_name, extension, is_folder=False, notify=False)
        else:
            logger.info(f"File '{filename}' does not match the naming convention.")
            self.prompt_rename(file_path, filename, is_folder=False)

    def process_elid_folder(self, folder_path):
        # Get the folder name
        folder_name = os.path.basename(folder_path)
        if not self.is_elid_folder(folder_path):
            logger.info(f"Folder '{folder_name}' does not contain an .elid file.")
            # move the folder to the exceptions folder
            new_path = os.path.join(self.exceptions_dir, folder_name)
            try:
                os.rename(folder_path, new_path)
                logger.info(f"Folder moved from '{folder_path}' to '{new_path}'.")
            except Exception as e:
                logger.exception(f"Failed to move folder '{folder_path}' to '{new_path}': {e}")
            return

        if self.is_valid_name(folder_name):
            # Folder meets the standard, rename accordingly
            self.rename_item(folder_path, folder_name, is_folder=True, notify=False)
        else:
            logger.info(f"Folder '{folder_name}' does not match the naming convention.")
            self.prompt_rename(folder_path, folder_name, is_folder=True)

    def construct_names_and_id(self, base_name, extension):
        date_str = datetime.datetime.now().strftime('%Y%m%d')

        # Scrub the base_name
        base_name = self.scrub_input(base_name)

        institute, user_ID, sample_ID = base_name.split('_')

        # The name of the record is the sample name
        record_name = sample_ID

        # Construct the record ID (Device_ID-Date-Institute-User_ID)
        record_ID = f"{self.device_ID}-{date_str}-{institute}-{user_ID}"
        
        # Prepare path without counter
        new_path = os.path.join(self.processed_dir, base_name + extension)
        # Ensure uniqueness by adding counter
        unique_new_path = self.get_unique_path(new_path)
        return record_name, record_ID, unique_new_path

    def rename_item(self, path, base_name, extension="", is_folder=False, notify=True):
        """
        Renames a file or folder by appending the device name prefix, date suffix, and counter.
        Moves the file or folder to the validated folder.
        """
        # Construct the new name
        record_name, record_ID, new_path = self.construct_names_and_id(base_name, extension)

        try:
            os.rename(path, new_path)
            if notify:
                self.gui_manager.show_info("Success", f"{'Folder' if is_folder else 'File'} renamed to '{os.path.basename(new_path)}'")
            logger.info(f"{'Folder' if is_folder else 'File'} '{path}' renamed to '{new_path}'.")

            # Check if the record is already in the archive
            if self.record_in_archive(record_name, ARCHIVED_FILES_JSON):
                if self.gui_manager.prompt_append_record(record_name):
                    self.update_records(record_name, record_ID, new_path)
                    self.manage_session()
                else:
                    self.prompt_rename(path, os.path.basename(path), existing_record=True, is_folder=is_folder)
            else:
                self.update_records(record_name, record_ID, new_path)
                self.manage_session()

        except Exception as e:
            self.gui_manager.show_error("Error", f"Failed to rename {'folder' if is_folder else 'file'}: {e}")
            logger.exception(f"Failed to rename {'folder' if is_folder else 'file'} '{path}' to '{new_path}': {e}")
            self.move_to_rename_folder(path, os.path.basename(path), is_folder=is_folder)

    def prompt_rename(self, path, name, existing_record=False, is_folder=False):
        if existing_record:
            message = (
                f"Rename '{name}' to create new record.\n"
            )
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
            # Construct base_name
            base_name = f"{institute}_{user_ID}_{sample_ID}"
            # Now rename the file or folder
            self.rename_item(path, base_name, extension, is_folder=is_folder, notify=True)
            break

    def move_to_rename_folder(self, path, name, is_folder=False):
        new_path = self.generate_rename_filename(name)
        try:
            os.rename(path, new_path)
            self.gui_manager.show_info(
                "Moved",
                f"Renaming was cancelled or failed. The {'folder' if is_folder else 'file'} has been moved to: {new_path}"
            )
            logger.info(f"{'Folder' if is_folder else 'File'} moved from '{path}' to '{new_path}'.")
        except Exception as e:
            self.gui_manager.show_error("Error", f"Failed to move {'folder' if is_folder else 'file'}: {e}")
            logger.exception(f"Failed to move {'folder' if is_folder else 'file'} '{path}' to '{new_path}': {e}")
        
    #endregion


# DeviceWatchdogApp combines file naming monitoring, metadata extraction, and session management, orchestrating the entire process
# it handles session ends, triggering file syncing, and maintaining an up-to-date list of processed records
class DeviceWatchdogApp:
    """
    Main application class that combines file naming monitoring, metadata extraction,
    and session management.
    """
    def __init__(
        self,
        watch_dir,
        device_name,
        rename_folder,
        processed_dir,
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

        if testing:
            # delete all files and folders in watch_dir
            for root, dirs, files in os.walk(watch_dir):
                for file in files:
                    os.remove(os.path.join(root, file))
                for dir in dirs:
                    shutil.rmtree(os.path.join(root, dir))

        self.session_timeout = session_timeout  # Session timeout in seconds

        # Initialize GUIManager
        self.gui_manager = GUIManager()

        # Initialize SessionManager
        self.session_manager = SessionManager(session_timeout, self.end_session, self.gui_manager.root)

        # Ensure the necessary directories exist
        os.makedirs(rename_folder, exist_ok=True)
        os.makedirs(processed_dir, exist_ok=True)
        os.makedirs(archive_dir, exist_ok=True)
        os.makedirs(exceptions_dir, exist_ok=True)

        # Initialize the processed files dictionary
        self.processed_files = {}

        # Initialize FileProcessor
        self.file_processor = FileProcessor(
            device_ID=device_name,
            rename_folder=rename_folder,
            processed_dir=processed_dir,
            exceptions_dir=exceptions_dir,
            input_pattern=FILENAME_PATTERN,
            gui_manager=self.gui_manager,
            session_manager=self.session_manager
        )

        # Initialize event queue and session event
        self.event_queue = queue.Queue()
        self.session_event = threading.Event()
        self.session_active = False
        self.session_timer = None

        # Set up the observer and event handler
        self.event_handler = FileEventHandler(self.event_queue)
        self.observer = Observer()
        self.observer.schedule(self.event_handler, path=self.watch_dir, recursive=False)
        self.observer.start()
        logger.info(f"Monitoring directory: {self.watch_dir}")

        # Schedule the event processing method
        self.gui_manager.root.after(100, self.process_events)

        # Set up the window close protocol
        self.gui_manager.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Set the exception handler for Tkinter
        self.gui_manager.root.report_callback_exception = self.handle_exception

    def update_archived_files_list(self):
        """
        Saves the dictionary of processed files to a JSON file.
        """
        archived_files_path = os.path.join(self.archive_dir, 'processed_files.json')
        try:
            with open(archived_files_path, 'w') as f:
                json.dump(self.processed_files, f, indent=4)
            logger.info("Processed files data saved.")
        except Exception as e:
            logger.exception(f"Failed to save processed files data: {e}")

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        """
        Handles unexpected exceptions by displaying an error message and logging the exception.
        """
        logger.error("An unexpected error occurred", exc_info=(exc_type, exc_value, exc_traceback))
        self.gui_manager.show_error(
            "Application Error",
            "An unexpected error occurred. Please contact the administrator."
        )
        self.on_closing()

    def end_session(self):
        """
        Ends the current session, syncs files, and moves them to the archive folder.
        Ensures that all operations are completed atomically.
        """
        try:
            self.session_active = False
            if self.session_timer:
                self.session_timer.cancel()
            logger.info("Session ended.")

            # Sync files to the database
            self.sync_files_to_database()

        except Exception as e:
            logger.exception(f"An error occurred during session end: {e}")
            self.gui_manager.show_error("Session End Error", f"An error occurred during session end: {e}")
        finally:
            # Ensure that the session is properly closed
            if hasattr(self.gui_manager, 'done_dialog') and self.gui_manager.done_dialog.winfo_exists():
                self.gui_manager.done_dialog.destroy()

    def sync_files_to_database(self):
        """
        Syncs files to the database and updates the processed files tracking dictionary.
        """
        logger.info("Syncing files to the database...")

        records_dict = self.file_processor.get_record_dict_for_sync()

        for local_record in records_dict.values():
            local_record: LocalRecord

            local_record.sync_to_database(self.archive_dir)

            # Update the processed files dictionary
            num_files = local_record.get_file_count()
            self.processed_files[local_record.record_name] = self.processed_files.get(local_record.record_name, 0) + num_files
            logger.info(f"Updated count for base '{local_record.record_name}': {self.processed_files[local_record.record_name]} files.")

        # Clear records after processing
        self.file_processor.clear_records_dict()
        self.update_archived_files_list()
        logger.info("Files have been synced to the database.")

    def process_events(self):
        """
        Processes file events from the queue. This method is called periodically, and looks for new files to process.
        """
        while not self.event_queue.empty():
            data_path = self.event_queue.get()
            self.file_processor.process_incoming_file_or_folder(data_path)
        self.gui_manager.root.after(100, self.process_events)

        # if testing, add a file or folder into the watch directory
        if self.testing:
            if os.path.isfile(self.test_path):
                shutil.copy(self.test_path, self.watch_dir)
            elif os.path.isdir(self.test_path):
                shutil.copytree(self.test_path, os.path.join(self.watch_dir, os.path.basename(self.test_path)))
            self.testing = False

        # reset the daily counter of the file_processor at the start of each day
        if datetime.datetime.now().hour == 0:
            self.file_processor.reset_daily_counter()

    def on_closing(self):
        """
        Handles the application closing event.
        """
        if self.session_timer:
            self.session_timer.cancel()
        self.observer.stop()
        self.observer.join()
        self.gui_manager.destroy()
        logger.info("Monitoring stopped.")

    def run(self):
        """
        Starts the Tkinter main loop.
        """
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
        session_timeout=60,  # Timeout in seconds
        testing=testing,
    )
    try:
        app.run()
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
    finally:
        logger.info("Application closed.")
