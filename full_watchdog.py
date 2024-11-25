import os
import re
import sys
import json
import queue
import time
import logging
import threading
import datetime
import hashlib
import tifffile
import tkinter as tk
from tkinter import simpledialog, messagebox
from collections import defaultdict
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import xml.etree.ElementTree as ET

from kadi_apy import KadiManager

watch_dir = r"test_monitor"
rename_folder = os.path.join(watch_dir, 'To_Rename')
processed_dir = os.path.join(watch_dir, 'Validated')
archive_dir = os.path.join(watch_dir, 'Archive')

# Configure logging
logging.basicConfig(filename='watchdog.log',level=logging.INFO, format='%(asctime)s - %(message)s')


# Regular expression pattern for the required file naming convention.
pattern = re.compile(r'^[A-Za-z0-9]+_[A-Za-z0-9]+_[A-Za-z0-9]+_[A-Za-z0-9]+_\d{4}-\d{2}-\d{2}$')

def get_base_name(file_name):
    """
    Extracts the base name of a file, treating it as a base if it lacks a '_number' suffix.
    If the file has a '_number' suffix (1-2 digits), this method removes the suffix to get the base name.

    Args:
        file_name (str): The name of the file.

    Returns:
        str: The base name of the file.
    """
    # Regex to detect '_number' suffix at the end of the filename (1 or more digits)
    suffix_pattern = re.compile(r'_(\d+)\.(tiff|tif|json)$')
    match = suffix_pattern.search(file_name)
    if match:
        # If suffix exists, derive the base name by removing '_number' and extension
        return file_name[:match.start()]
    else:
        # If no suffix, remove the file extension
        return os.path.splitext(file_name)[0]

class FileEventHandler(FileSystemEventHandler):
    """
    Event handler that processes new files.
    """
    def __init__(self, app):
        super().__init__()
        self.app = app

    def on_created(self, event):
        if not event.is_directory:
            # Add a newly added file path to the queue
            self.app.event_queue.put(event.src_path)
            logging.info(f"New file detected: {event.src_path}")

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

class MultiFieldDialog(simpledialog.Dialog):
    """
    Custom dialog to collect Name, Institute, and Data Qualifier.
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

class MetadataExtractor:
    """
    Class to handle metadata extraction from TIFF files.
    """
    @staticmethod
    def hash_file(file_path):
        """
        Generates a hash for the file at the specified path.
        """
        try:
            hasher = hashlib.md5()
            with open(file_path, 'rb') as file:
                while True:
                    data = file.read(65536)  # 64 KB chunks
                    if not data:
                        break
                    hasher.update(data)
            return hasher.hexdigest()
        except Exception as e:
            logging.error(f"Failed to hash file {file_path}: {e}")
            return None

    @staticmethod
    def flatten_dictionary(d, parent_key='', sep='_'):
        """
        Recursively flattens a nested dictionary.
        """
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(MetadataExtractor.flatten_dictionary(v, new_key, sep=sep).items())
            elif isinstance(v, (list, tuple)):
                for i, item in enumerate(v):
                    items.extend(MetadataExtractor.flatten_dictionary({f"{k}_{i}": item}, parent_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    @staticmethod
    def parse_xml_metadata(xml_string, file_name):
        """
        Parses XML string and returns a flat dictionary.
        """
        try:
            root = ET.fromstring(xml_string)
            xml_dict = MetadataExtractor.etree_to_dict(root, file_name)
            return xml_dict
        except Exception as e:
            logging.error(f"Failed to parse XML metadata: {e}")
            return {}

    @staticmethod
    def etree_to_dict(element, file_name, parent_key='', sep='_'):
        """
        Converts an ElementTree element into a flat dictionary.
        """
        items = {}
        unit = element.attrib.get('unit', 'no-unit')
        tag_name = element.tag
        key = tag_name

        full_key = f"{file_name}_{key}_{unit}"

        # If the element has text, use it as the value
        text = element.text.strip() if element.text else None
        if text:
            items[full_key] = text

        # Process attributes (other than 'unit')
        for attr_name, attr_value in element.attrib.items():
            if attr_name != 'unit':
                attr_key = f"{file_name}_{key}{sep}{attr_name}_no-unit"
                items[attr_key] = attr_value

        # Recursively process child elements
        for child in element:
            items.update(MetadataExtractor.etree_to_dict(child, file_name, key, sep))

        return items

    @staticmethod
    def extract_metadata(file_path):
        """
        Extracts metadata from an SEM TIFF file and returns it as a flat dictionary.
        """
        base_name = os.path.basename(file_path)
        file_name, ext = os.path.splitext(base_name)
        file_hash = MetadataExtractor.hash_file(file_path)

        metadata = {}
        try:
            with tifffile.TiffFile(file_path) as tif:
                # Extract tags from the first page
                page = tif.pages[0]
                tags = page.tags

                # Process TIFF tags
                for tag in tags.values():
                    tag_name = tag.name
                    tag_value = tag.value
                    # Convert bytes to string if necessary
                    if isinstance(tag_value, bytes):
                        try:
                            tag_value = tag_value.decode('utf-8')
                        except UnicodeDecodeError:
                            tag_value = tag_value.decode('latin-1')

                    # For TIFF tags, unit is 'no-unit' by default
                    key = f"{file_name}_{tag_name}_no-unit"
                    metadata[key] = tag_value

                    # Check if tag_name is 'FEI_TITAN' to parse embedded XML
                    if tag_name == "FEI_TITAN":
                        # Parse embedded XML
                        xml_metadata = MetadataExtractor.parse_xml_metadata(tag_value, file_name)
                        
                        # Remove the top-level key, as it is extraneous from the SEM output
                        if xml_metadata:
                            FeiImage_key = next(iter(xml_metadata))
                            xml_metadata.pop(FeiImage_key)

                            # Update metadata dictionary with the parsed XML metadata
                            metadata.update(xml_metadata)

            # Add file hash to metadata
            metadata[f"{file_name}_filehash_no-unit"] = file_hash

            # Flatten the metadata dictionary
            metadata = MetadataExtractor.flatten_dictionary(metadata)

        except Exception as e:
            logging.error(f"Failed to extract metadata from {file_path}: {e}")
            return None
        return metadata

class DeviceWatchdogApp:
    """
    Main application class that combines file naming monitoring, metadata extraction,
    and session management.
    """
    def __init__(self, watch_dir, device_name, rename_folder, processed_dir, archive_dir, session_timeout=60):
        self.watch_dir = watch_dir
        self.device_name = device_name
        self.rename_folder = rename_folder
        self.processed_dir = processed_dir
        self.archive_dir = archive_dir
        self.session_timeout = session_timeout  # Session timeout in seconds

        # Ensure the necessary directories exist
        os.makedirs(self.rename_folder, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)
        os.makedirs(self.archive_dir, exist_ok=True)

        # Initialize Tkinter root
        self.root = tk.Tk()
        self.root.withdraw()  # Hide the root window

        # Create a dialog parent window
        self.dialog_parent = tk.Toplevel(self.root)
        self.dialog_parent.withdraw()
        self.dialog_parent.attributes("-topmost", True)

        # Initialize event queue and session event
        self.event_queue = queue.Queue()
        self.session_event = threading.Event()
        self.session_active = False
        self.session_timer = None

        # Set up the observer and event handler
        self.event_handler = FileEventHandler(self)
        self.observer = Observer()
        self.observer.schedule(self.event_handler, path=self.watch_dir, recursive=False)
        self.observer.start()
        logging.info(f"Monitoring directory: {self.watch_dir}")

        # Schedule the event processing method
        self.root.after(100, self.process_events)

        # Set up the window close protocol
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Set the exception handler for Tkinter
        self.root.report_callback_exception = self.handle_exception

        # Initialize the processed files dictionary
        self.processed_files = self.load_processed_files()

    def load_processed_files(self):
        """
        Loads the dictionary of processed files from a JSON file, if it exists.
        """
        processed_files_path = os.path.join(self.archive_dir, 'processed_files.json')
        if os.path.exists(processed_files_path):
            try:
                with open(processed_files_path, 'r') as f:
                    processed_files = json.load(f)
                logging.info("Loaded processed files data.")
                return processed_files
            except Exception as e:
                logging.error(f"Failed to load processed files data: {e}")
                return {}
        else:
            return {}

    def save_processed_files(self):
        """
        Saves the dictionary of processed files to a JSON file.
        """
        processed_files_path = os.path.join(self.archive_dir, 'processed_files.json')
        try:
            with open(processed_files_path, 'w') as f:
                json.dump(self.processed_files, f, indent=4)
            logging.info("Processed files data saved.")
        except Exception as e:
            logging.error(f"Failed to save processed files data: {e}")

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        """
        Handles unexpected exceptions by displaying an error message and logging the exception.
        """
        logging.error("An unexpected error occurred", exc_info=(exc_type, exc_value, exc_traceback))
        messagebox.showerror(
            "Application Error",
            "An unexpected error occurred. Please contact the administrator.",
            parent=self.dialog_parent
        )
        self.on_closing()

    def start_session(self):
        """
        Starts a new session and initializes the session timer.
        """
        if not self.session_active:
            self.session_active = True
            logging.info("Session started.")
            self.start_timer()
            self.show_done_dialog()

    def start_timer(self):
        """
        Starts or restarts the session timer.
        """
        if self.session_timer:
            self.session_timer.cancel()
        self.session_timer = threading.Timer(self.session_timeout, self.end_session)
        self.session_timer.start()
        logging.info("Session timer started/restarted.")

    def end_session(self):
        """
        Ends the current session, syncs files, and moves them to the archive folder.
        """
        self.session_active = False
        if self.session_timer:
            self.session_timer.cancel()
        logging.info("Session ended.")

        # Sync files to the database
        self.sync_files_to_database()

        # Move files to the archive directory
        self.archive_files()

        # Close the "Done" dialog if it's open
        if hasattr(self, 'done_dialog') and self.done_dialog.winfo_exists():
            self.done_dialog.destroy()

    def sync_files_to_database(self):
        """
        Syncs files to the database and updates the processed files tracking dictionary.
        """
        logging.info("Syncing files to the database...")
        with KadiManager() as manager:
            grouped_files = self.group_files_by_base_name()
            self.combine_json_files(grouped_files)
            self.upload_files_to_database(manager, grouped_files)
        self.save_processed_files()
        logging.info("Files have been synced to the database.")

    def group_files_by_base_name(self):
        """
        Groups files in the processed directory by their base name.
        """
        grouped_files = defaultdict(list)
        for file in os.listdir(self.processed_dir):
            base_name = get_base_name(file)
            grouped_files[base_name].append(file)
        return grouped_files

    def combine_json_files(self, grouped_files):
        """
        Combines individual JSON files into a single metadata file for each base name.
        """
        for base_name, files in grouped_files.items():
            combined_data = []
            for file in files:
                if file.endswith('.json') and get_base_name(file) == base_name:
                    file_path = os.path.join(self.processed_dir, file)
                    try:
                        with open(file_path, 'r') as f:
                            file_data = json.load(f)
                            combined_data.append(file_data)
                            logging.info(f"Successfully read file: {file}")
                    except (json.JSONDecodeError, OSError) as e:
                        logging.error(f"Error reading or parsing file '{file}': {e}")
            if combined_data:
                output_file = os.path.join(self.processed_dir, f"{base_name}_metadata.json")
                try:
                    with open(output_file, 'w') as f:
                        json.dump(combined_data, f, indent=4)
                    logging.info(f"Combined data for base '{base_name}' saved to {output_file}")
                    grouped_files[base_name].append(f"{base_name}_metadata.json")
                except OSError as e:
                    logging.error(f"Error writing combined file '{output_file}': {e}")
                # Remove individual JSON files after combining
                for file in files.copy():
                    if file.endswith('.json') and get_base_name(file) == base_name:
                        file_path = os.path.join(self.processed_dir, file)
                        try:
                            os.remove(file_path)
                            grouped_files[base_name].remove(file)
                            logging.info(f"Removed individual JSON file: {file}")
                        except OSError as e:
                            logging.error(f"Error removing file '{file}': {e}")
            else:
                logging.warning(f"No valid data to combine for base name '{base_name}'. Skipping.")

    def upload_files_to_database(self, manager, grouped_files):
        """
        Uploads files to the database and updates the processed files dictionary.
        """
        for base_name, files in grouped_files.items():
            record = manager.record(create=True, identifier=base_name)
            for file in files:
                file_path = os.path.join(self.processed_dir, file)
                record.upload_file(file_path)
                logging.info(f"Uploaded file: {file}")
            # Update the processed files dictionary
            num_files = len(files)
            self.processed_files[base_name] = self.processed_files.get(base_name, 0) + num_files
            logging.info(f"Updated count for base '{base_name}': {self.processed_files[base_name]} files.")

    def archive_files(self):
        """
        Moves files from the processed folder to the archive folder.
        """
        logging.info("Archiving files...")
        for file_name in os.listdir(self.processed_dir):
            file_path = os.path.join(self.processed_dir, file_name)
            if os.path.isfile(file_path):
                dest_path = os.path.join(self.archive_dir, file_name)
                dest_path = self.get_unique_path(dest_path)
                try:
                    os.rename(file_path, dest_path)
                    logging.info(f"Moved '{file_name}' to '{self.archive_dir}'.")
                except Exception as e:
                    logging.error(f"Failed to move file '{file_name}': {e}")
        logging.info("Archiving completed.")

    # TODO: Consider this method a helper function and move outside the class (if appropriate)
    def get_unique_path(self, dest_path):
        """
        Generates a unique file path to avoid overwriting existing files.
        """
        # TODO: Always add a counter to the filename to ensure uniqueness, and improve findability
        directory, filename = os.path.split(dest_path)
        base, extension = os.path.splitext(filename)
        counter = 1
        unique_filename = filename
        while os.path.exists(os.path.join(directory, unique_filename)):
            unique_filename = f"{base}_{counter}{extension}"
            counter += 1
        return os.path.join(directory, unique_filename)

    def show_done_dialog(self):
        """
        Displays a dialog with a "Done" button for the user to manually end the session.
        """
        self.done_dialog = tk.Toplevel(self.root)
        self.done_dialog.title("Session Active")
        self.done_dialog.attributes("-topmost", True)
        label = tk.Label(self.done_dialog, text="A session is in progress. Click 'Done' when finished.")
        label.pack(padx=20, pady=10)
        done_button = tk.Button(self.done_dialog, text="Done", command=self.end_session)
        done_button.pack(pady=10)
        # Handle dialog close event
        self.done_dialog.protocol("WM_DELETE_WINDOW", self.on_done_dialog_close)

    def on_done_dialog_close(self):
        """
        Prevents the user from closing the dialog without clicking 'Done'.
        """
        pass  # Do nothing to prevent closing the dialog

    def process_events(self):
        """
        Processes file events from the queue. Thi method is called periodically, and looks for new files to process.
        """
        while not self.event_queue.empty():
            file_path = self.event_queue.get()
            self.check_file_name(file_path)
        self.root.after(100, self.process_events)

    def check_file_name(self, file_path):
        """
        Checks if the file name matches the required naming convention.
        If not, prompts the user to rename the file.
        """
        filename = os.path.basename(file_path)
        base_name, extension = os.path.splitext(filename)

        # If the file is a JSON file, do not check the naming convention
        if extension.lower() == '.json':
            logging.info(f"File '{filename}' is a JSON file.")
            return

        # If the file is not a TIFF file, alert the user and move the file to a 'rename' folder
        if extension.lower() not in ['.tiff', '.tif']:
            logging.info(f"File '{filename}' is not a TIFF file.")
            self.move_to_rename_folder(file_path, filename)
            return

        # Check if the base name matches the pattern
        if pattern.match(base_name):
            # The file name matches the pattern; proceed to rename ensuring uniqueness
            # TODO: Add functionality to ensure that a validated file is not lost here in the event of an exception
            self.rename_file(file_path, filename, notify=False)
        else:
            logging.info(f"File '{filename}' does not match the naming convention.")
            self.prompt_rename(file_path, filename)

    def prompt_rename(self, file_path, filename):
        """
        Prompts the user to rename the file using a graphical dialog.
        If the user cancels, moves the file to a 'rename' folder.
        """
        message = (
            f"The file '{filename}' does not adhere to the naming convention.\n"
            f"The required naming format is: DeviceName_Institute_Name_DataQualifier_Date (e.g., SEM_IPAT_MuS_Sample-Name_2023-10-19)"
        )

        messagebox.showwarning("Invalid File Name", message, parent=self.dialog_parent)

        # TODO: Add context manager to ensure any failure in renaming sends the file to the 'rename' folder
        while True:
            dialog = MultiFieldDialog(self.root, "Rename File")
            if dialog.result is None:
                # User cancelled the dialog
                self.move_to_rename_folder(file_path, filename)
                return

            user_ID = dialog.result['name']
            institute = dialog.result['institute']
            sample_ID = dialog.result['sample_ID']

            # Check that none of the fields are empty
            if not user_ID or not institute or not sample_ID:
                messagebox.showwarning(
                    "Incomplete Information",
                    "All fields are required. Please fill in all fields.",
                    parent=self.dialog_parent
                )
                continue

            # Remove spaces and special characters to ensure the filename is valid
            # TODO: Consider requirements for cleansing the input fields
            user_ID = re.sub(r'\W+', '', user_ID)
            institute = re.sub(r'\W+', '', institute)
            sample_ID = re.sub(r'[^\w-]+', '', sample_ID)

            # Generate date string
            date_str = datetime.datetime.now().strftime('%Y-%m-%d')
            # Construct the new base name
            new_base_name = f"{self.device_name}_{institute}_{user_ID}_{sample_ID}_{date_str}"

            # Now, check if new_base_name matches the pattern
            if pattern.match(new_base_name):
                new_name = new_base_name + os.path.splitext(filename)[1]
                self.rename_file(file_path, new_name, notify=True)
                break
            else:
                messagebox.showwarning(
                    "Invalid File Name",
                    "The new file name does not match the required format or contains invalid characters. Please try again.",
                    parent=self.dialog_parent
                )

    def move_to_rename_folder(self, file_path, filename):
        """
        Moves the file to a 'rename' folder if the user cancels the renaming process.
        """
        rename_folder = self.rename_folder

        # Get the file extension
        _, extension = os.path.splitext(filename)
        # Get the current date
        date_str = datetime.datetime.now().strftime('%Y%m%d')
        # Construct the new filename
        new_filename = f"{self.device_name}_rename-file_{date_str}{extension}"

        new_path = self.get_unique_path(os.path.join(rename_folder, new_filename))

        try:
            os.rename(file_path, new_path)
            messagebox.showinfo(
                "File Moved",
                f"File renaming was cancelled. The file has been moved to: {new_path}", parent=self.dialog_parent
            )
            logging.info(f"File moved to '{new_path}'.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to move file: {e}")
            logging.error(f"Failed to move file '{file_path}' to '{new_path}': {e}")

    def rename_file(self, file_path, new_name, notify=True):
        """
        Renames the file to the new name provided by the user, ensuring uniqueness.
        """
        new_path = os.path.join(self.processed_dir, new_name)
        new_path = self.get_unique_path(new_path)

        try:
            os.rename(file_path, new_path)
            if notify:
                messagebox.showinfo("Success", f"File renamed to '{os.path.basename(new_path)}'", parent=self.dialog_parent)
            logging.info(f"File '{file_path}' renamed to '{new_path}'.")

            # After renaming and moving the file, extract metadata
            self.extract_and_save_metadata(new_path)

            # Start or restart session timer
            if not self.session_active:
                self.start_session()
            else:
                self.start_timer()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to rename file: {e}", parent=self.dialog_parent)
            logging.error(f"Failed to rename file '{file_path}' to '{new_path}': {e}")

    def extract_and_save_metadata(self, file_path):
        """
        Extracts metadata from a TIFF file and saves it as a JSON file.
        """
        metadata = MetadataExtractor.extract_metadata(file_path)
        if metadata:
            json_file_name = os.path.splitext(os.path.basename(file_path))[0] + '.json'
            json_file_path = os.path.join(self.processed_dir, json_file_name)
            try:
                with open(json_file_path, 'w') as json_file:
                    json.dump(metadata, json_file, indent=4)
                logging.info(f"Metadata extracted and saved to {json_file_path}")
            except Exception as e:
                logging.error(f"Failed to save JSON data: {e}")
        else:
            logging.error(f"No metadata extracted from {file_path}")

    def on_closing(self):
        """
        Handles the application closing event.
        """
        if self.session_timer:
            self.session_timer.cancel()
        self.observer.stop()
        self.observer.join()
        self.dialog_parent.destroy()
        self.root.destroy()
        logging.info("Monitoring stopped.")

    def run(self):
        """
        Starts the Tkinter main loop.
        """
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.on_closing()
        except Exception:
            self.handle_exception(*sys.exc_info())

if __name__ == "__main__":
    app = DeviceWatchdogApp(
        watch_dir=watch_dir,
        device_name="SEM",
        rename_folder=rename_folder,
        processed_dir=processed_dir,
        archive_dir=archive_dir,
        session_timeout=60  # Timeout in seconds
    )
    app.run()
