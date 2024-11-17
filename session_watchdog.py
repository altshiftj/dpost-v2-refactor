import os
import sys
import queue
import logging
import threading
import re
import json  # Added import for JSON handling
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
    suffix_pattern = re.compile(r'_(\d{1,2})\.(tiff|json)$')
    match = suffix_pattern.search(file_name)
    if match:
        # If suffix exists, derive the base name by removing '_number' and extension
        return file_name[:match.start()]
    else:
        # If no suffix, remove the file extension
        return os.path.splitext(file_name)[0]

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

        # Initialize a dictionary to store metadata
        self.metadata_store = {}

        # Initialize the processed files dictionary
        self.processed_files = self.load_processed_files()  # New line

    def load_processed_files(self):
        """
        Loads the dictionary of processed files from a JSON file, if it exists.
        """
        processed_files_path = os.path.join(self.processed_dir, 'processed_files.json')
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
        processed_files_path = os.path.join(self.processed_dir, 'processed_files.json')
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
        Ends the current session, syncs files, and moves them to the processed folder.
        """
        self.session_active = False
        if self.session_timer:
            self.session_timer.cancel()
        logging.info("Session ended.")

        # Sync files to the database
        self.sync_files_to_database()

        # Move files to the processed directory
        self.archive_files()

        # Close the "Done" dialog if it's open
        if hasattr(self, 'done_dialog') and self.done_dialog.winfo_exists():
            self.done_dialog.destroy()

    def sync_files_to_database(self):
        """
        Syncs files to the database and updates the processed files tracking dictionary.
        """
        # Sync files to the database
        logging.info("Syncing files to the database...")

        with KadiManager() as manager:
            # Group the files by base name
            grouped_files = defaultdict(list)
            for file in os.listdir(self.path_to_watch):
                base_name = get_base_name(file)
                grouped_files[base_name].append(file)

            # Combine the JSON files in each group into a single file
            for base_name, files in grouped_files.items():
                combined_data = []
                for file in files:
                    if file.endswith('.json'):
                        # Ensure the file's base name matches the group base_name
                        file_base_name = get_base_name(file)
                        if file_base_name != base_name:
                            continue  # Skip JSON files that don't match the base name
                        file_path = os.path.join(self.path_to_watch, file)
                        try:
                            with open(file_path, 'r') as f:
                                file_data = json.load(f)
                                combined_data.append(file_data)  # Corrected: remove extra list wrapping
                                logging.info(f"Successfully read file: {file}")
                        except (json.JSONDecodeError, OSError) as e:
                            logging.error(f"Error reading or parsing file '{file}': {e}")
                            continue

                # Skip creating a combined file if no valid data
                if not combined_data:
                    logging.warning(f"No valid data to combine for base name '{base_name}'. Skipping.")
                    continue

                # Create a combined file for this group
                output_file = os.path.join(self.path_to_watch, f"{base_name}_metadata.json")
                try:
                    with open(output_file, 'w') as f:
                        json.dump(combined_data, f, indent=4)
                    logging.info(f"Combined data for base '{base_name}' saved to {output_file}")
                    grouped_files[base_name].append(f"{base_name}_metadata.json")
                except OSError as e:
                    logging.error(f"Error writing combined file '{output_file}': {e}")

                # Remove individual JSON files after combining
                for file in files:
                    if file.endswith('.json') and get_base_name(file) == base_name:
                        file_path = os.path.join(self.path_to_watch, file)
                        try:
                            # Remove the individual JSON file from the group
                            grouped_files[base_name].remove(file)
                            os.remove(file_path)
                            logging.info(f"Removed individual JSON file: {file}")
                        except OSError as e:
                            logging.error(f"Error removing file '{file}': {e}")

            # Continue with uploading files and processing metadata
            for base_name, files in grouped_files.items():
                record = manager.record(
                    create=True,
                    identifier=base_name,
                )

                for file in files:
                    file_path = os.path.join(self.path_to_watch, file)
                    record.upload_file(file_path)
                    logging.info(f"Uploaded file: {file}")

                # Retrieve metadata for the base_name
                metadata = self.metadata_store.get(base_name)
                if metadata:
                    record.add_metadata(metadata)
                    logging.info(f"Added metadata for base '{base_name}'.")
                else:
                    logging.warning(f"No metadata found for base '{base_name}'.")

                # Update the processed files dictionary
                num_files = len(files)
                if base_name in self.processed_files:
                    self.processed_files[base_name] += num_files
                    logging.info(f"Updated count for base '{base_name}': {self.processed_files[base_name]} files.")
                else:
                    self.processed_files[base_name] = num_files
                    logging.info(f"Added new base '{base_name}' with count: {num_files} files.")

            # Save the processed files dictionary after syncing all files
            self.save_processed_files()

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
            base_name = get_base_name(os.path.basename(file_path))

            # Assume that the metadata is already prepared and can be stored
            # For example, we can extract metadata here and store it
            metadata = extract_metadata(file_path)
            if metadata:
                self.metadata_store[base_name] = metadata
                logging.info(f"Metadata stored for base '{base_name}'.")
            else:
                logging.warning(f"No metadata extracted from '{file_path}'.")

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

def extract_metadata(file_path):
    """
    Extracts metadata from the TIFF file and returns it as a dictionary.
    This function assumes that the metadata extraction is handled here.
    """
    # Placeholder for actual metadata extraction logic
    # For example, use tifffile or other libraries to extract metadata
    metadata = {}

    # Since dictionaries are to be settled before arriving here,
    # you should implement the actual metadata extraction elsewhere
    return metadata

if __name__ == "__main__":
    path_to_watch = r"test_monitor\Processed"
    archive_dir = r"test_monitor\Archive"
    app = FileMonitorApp(path_to_watch, archive_dir, session_timeout=60)  # Timeout in seconds
    app.run()
