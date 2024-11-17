import os
import sys
import queue
import logging
import datetime
import threading
import json
import re
from collections import defaultdict
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import tkinter as tk
from tkinter import messagebox

from kadi_apy import KadiManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def get_base_name(file_name):
    """
    Extracts the base name of a file, treating it as a base if it lacks a '_number' suffix.
    If the file has a '_number' suffix (1-2 digits), removes the suffix to get the base name.
    
    Args:
        file_name (str): The name of the file.
    
    Returns:
        str: The base name of the file.
    """
    # Regex to detect '_number' suffix at the end of the filename (1 or 2 digits)
    suffix_pattern = re.compile(r'_(\d{1,2})\.(json|tiff)$')
    match = suffix_pattern.search(file_name)
    if match:
        # If suffix exists, derive the base name by removing '_number'
        return file_name[:match.start()]
    else:
        # If no suffix, remove the file extension
        return os.path.splitext(file_name)[0]

def combine_json_files(folder_path, base_name):
    """
    Combines JSON files in the specified folder into separate combined files.
    A file is treated as the base if it lacks a '_number' suffix at the end.
    Related files sharing the same base are grouped together.
    
    Args:
        folder_path (str): The path to the folder containing JSON files.
    
    Returns:
        list: List of paths to the combined JSON files.
    """
    try:
        # List all JSON files in the folder
        json_files = [f for f in os.listdir(folder_path) if f.endswith('.json')]
        json_files.sort()  # Ensure consistent ordering

        if not json_files:
            logging.error("No JSON files found in the specified folder.")
            raise ValueError("No JSON files found in the specified folder.")

        # Group files by base name
        grouped_files = defaultdict(list)
        for file in json_files:
            grouped_files[base_name].append(file)

        combined_files = []

        # Process each group
        for base_name, files in grouped_files.items():
            combined_data = []
            for file in files:
                file_path = os.path.join(folder_path, file)
                try:
                    with open(file_path, 'r') as f:
                        file_data = json.load(f)
                        combined_data.append([file_data])  # Wrap each file's data in a list
                        logging.info(f"Successfully read file: {file}")
                except (json.JSONDecodeError, OSError) as e:
                    logging.error(f"Error reading or parsing file '{file}': {e}")
                    continue  # Skip the problematic file and proceed

            # Skip creating a combined file if no valid data
            if not combined_data:
                logging.warning(f"No valid data to combine for base name '{base_name}'. Skipping.")
                continue

            # Create a combined file for this group
            output_file = os.path.join(folder_path, f"{base_name}_combined.json")
            try:
                with open(output_file, 'w') as f:
                    json.dump(combined_data, f, indent=4)
                logging.info(f"Combined data for base '{base_name}' saved to {output_file}")
                combined_files.append(output_file)
            except OSError as e:
                logging.error(f"Error writing combined file '{output_file}': {e}")

        # delete the original json files
        for file in json_files:
            file_path = os.path.join(folder_path, file)
            try:
                os.remove(file_path)
                logging.info(f"Deleted file: {file}")
            except OSError as e:
                logging.error(f"Error deleting file '{file}': {e}")

        return combined_files

    except Exception as e:
        logging.critical(f"An unexpected error occurred: {e}")
        raise

def flatten_json(json_file_path):
    """
    Flattens nested dictionaries in a JSON file and returns the flattened structure.

    :param json_file_path: Path to the JSON file to be flattened.
    :type json_file_path: str
    :return: A list of flattened dictionaries if the JSON contains multiple records.
    :rtype: list[dict]
    """
    def flatten_dict(d, parent_key='', sep='_'):
        """
        Helper function to recursively flatten a dictionary.

        :param d: Dictionary to flatten.
        :type d: dict
        :param parent_key: Key prefix for the current recursion level.
        :type parent_key: str
        :param sep: Separator to use in flattened keys.
        :type sep: str
        :return: Flattened dictionary.
        :rtype: dict
        """
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    # Load JSON file
    with open(json_file_path, 'r') as file:
        data = json.load(file)

    # Handle both single dictionary and list of dictionaries in JSON
    if isinstance(data, list):
        # Flatten each dictionary in the list
        return [flatten_dict(item) for item in data]
    elif isinstance(data, dict):
        # Flatten single dictionary
        return [flatten_dict(data)]
    else:
        raise ValueError("JSON file must contain a dictionary or a list of dictionaries.")

class FileSessionHandler(FileSystemEventHandler):
    """
    Event handler that monitors file creation events and manages session timing.
    """
    def __init__(self, event_queue, session_event):
        super().__init__()
        self.event_queue = event_queue
        self.session_event = session_event

    def on_created(self, event):
        if not event.is_directory:
            # Add the file path to the queue
            self.event_queue.put(event.src_path)
            # Signal that a file has arrived to manage session timing
            self.session_event.set()
            # Log the event
            logging.info(f"New file detected: {event.src_path}")

class FileMonitorApp:
    """
    Main application class that monitors a directory and manages file sessions.
    """
    def __init__(self, path_to_watch, processed_dir, session_timeout=60):
        self.path_to_watch = path_to_watch
        self.processed_dir = processed_dir
        self.session_timeout = session_timeout  # Session timeout in seconds

        # Ensure the processed directory exists
        os.makedirs(self.processed_dir, exist_ok=True)

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
        self.event_handler = FileSessionHandler(self.event_queue, self.session_event)
        self.observer = Observer()
        self.observer.schedule(self.event_handler, path=self.path_to_watch, recursive=False)
        self.observer.start()
        logging.info(f"Monitoring directory: {self.path_to_watch}")

        # Schedule the event processing method
        self.root.after(100, self.process_events)

        # Set up the window close protocol
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Set the exception handler for Tkinter
        self.root.report_callback_exception = self.handle_exception

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
        Ends the current session, syncs files, and moves them to the processed folder.
        """
        self.session_active = False
        if self.session_timer:
            self.session_timer.cancel()
        logging.info("Session ended.")

        # Sync files to the database (Placeholder function)
        self.sync_files_to_database()

        # Move files to the processed directory
        self.archive_files()

        # Close the "Done" dialog if it's open
        if hasattr(self, 'done_dialog') and self.done_dialog.winfo_exists():
            self.done_dialog.destroy()

    def sync_files_to_database(self):
        """
        Placeholder function for syncing files to a database.
        """
        logging.info("Syncing files to the database...")

        with KadiManager() as manager:
            # group the tiff files by the base name, they will be synced into the database as a single record
            grouped_files = defaultdict(list)
            for file in os.listdir(self.path_to_watch):
                if file.endswith('.tiff'):
                    base_name = get_base_name(file)
                    grouped_files[base_name].append(file)

            # combine json files in the session folder
            for base_name, files in grouped_files.items():
                combined_files = combine_json_files(self.path_to_watch, base_name)
                if combined_files:
                    logging.info(f"Combined files for base '{base_name}': {combined_files}")
                
                record = manager.record(
                    create = True,
                    identifier = base_name,
                )

                for file in files:
                    file_path = os.path.join(self.path_to_watch, file)
                    record.upload_file(file_path)
                    logging.info(f"Uploaded file: {file}")
                
                combined_files = flatten_json(combined_files)

                record.add_metadata(combined_files)
        logging.info("Files have been synced to the database.")

    def archive_files(self):
        """
        Moves files from the session folder to the processed folder.
        """
        logging.info("Archiving files...")
        for file_name in os.listdir(self.path_to_watch):
            file_path = os.path.join(self.path_to_watch, file_name)
            if os.path.isfile(file_path):
                dest_path = os.path.join(self.processed_dir, file_name)
                dest_path = self.get_unique_path(dest_path)
                try:
                    os.rename(file_path, dest_path)
                    logging.info(f"Moved '{file_name}' to '{self.processed_dir}'.")
                except Exception as e:
                    logging.error(f"Failed to move file '{file_name}': {e}")
        logging.info("Archiving completed.")

    def get_unique_path(self, dest_path):
        """
        Generates a unique file path to avoid overwriting existing files.
        """
        base, extension = os.path.splitext(dest_path)
        counter = 1
        while os.path.exists(dest_path):
            dest_path = f"{base}_{counter}{extension}"
            counter += 1
        return dest_path

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
        Processes file events from the queue.
        """
        while not self.event_queue.empty():
            file_path = self.event_queue.get()
            if not self.session_active:
                self.start_session()
            else:
                self.start_timer()
        self.root.after(100, self.process_events)

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
    path_to_watch = r"test_monitor\Processed"
    archive_dir = r"test_monitor\Archive"
    app = FileMonitorApp(path_to_watch, archive_dir, session_timeout=60)  # Timeout in seconds
    app.run()
