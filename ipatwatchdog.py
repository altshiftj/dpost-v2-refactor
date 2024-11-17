import re
import os
import sys
import queue
import logging
import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import tkinter as tk
from tkinter import simpledialog, messagebox

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Define the regular expression pattern for the required file naming convention.
pattern = re.compile(r'^[A-Za-z0-9]+_[A-Za-z]+_[A-Za-z]+_[A-Za-z0-9-]+_\d{8}$')

class FileNamingHandler(FileSystemEventHandler):
    """
    Event handler that adds file creation events to a queue.
    """
    def __init__(self, event_queue):
        super().__init__()
        self.event_queue = event_queue

    def on_created(self, event):
        if not event.is_directory:
            # Add the file path to the queue
            self.event_queue.put(event.src_path)
            # Log the event
            logging.info(f"New file detected: {event.src_path}")

class EntryWithPlaceholder(tk.Entry):
    """
    Custom Entry widget with placeholder text.
    """
    def __init__(self, master=None, placeholder="PLACEHOLDER", color='grey', *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.placeholder = placeholder
        self.placeholder_color = color
        self.default_fg_color = self['fg']

        # Remove focus-in binding
        # self.bind("<FocusIn>", self._focus_in)
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
        
        self.name_var = tk.StringVar()
        self.institute_var = tk.StringVar()
        self.data_qualifier_var = tk.StringVar()

        self.example_name = "Ex: MuS"
        self.example_institute = "Ex: IPAT"
        self.example_data_qualifier = "Ex: Cathode-20XD6-SO4"
        
        # Use EntryWithPlaceholder
        self.name_entry = EntryWithPlaceholder(master, self.example_name, textvariable=self.name_var)
        self.institute_entry = EntryWithPlaceholder(master, self.example_institute, textvariable=self.institute_var)
        self.data_qualifier_entry = EntryWithPlaceholder(master, self.example_data_qualifier, textvariable=self.data_qualifier_var)
        
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
        name = self.name_var.get()
        institute = self.institute_var.get()
        data_qualifier = self.data_qualifier_var.get()

        # Validate that the placeholders are not submitted
        if name == self.example_name:
            name = ""
        if institute == self.example_institute:
            institute = ""
        if data_qualifier == self.example_data_qualifier:
            data_qualifier = ""
        
        self.result = {
            'name': name,
            'institute': institute,
            'data_qualifier': data_qualifier,
        }


class FileMonitorApp:
    """
    Main application class that monitors a directory and ensures files adhere to a naming convention.
    """
    def __init__(self, path_to_watch, device_name, processed_dir, rename_folder):
        self.path_to_watch = path_to_watch
        self.device_name = device_name
        self.processed_dir = processed_dir
        self.rename_folder = rename_folder

        # Ensure the processed and rename directories exist
        os.makedirs(self.processed_dir, exist_ok=True)
        os.makedirs(self.rename_folder, exist_ok=True)

        # Initialize Tkinter root
        self.root = tk.Tk()
        self.root.withdraw()  # Hide the root window

        # Create a dialog parent window
        self.dialog_parent = tk.Toplevel(self.root)
        self.dialog_parent.withdraw()
        self.dialog_parent.attributes("-topmost", True)

        # Initialize event queue
        self.event_queue = queue.Queue()

        # Set up the observer and event handler
        self.event_handler = FileNamingHandler(self.event_queue)
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
            "The filename monitor has encountered unexpected error occurred. Please contact the administrator.",
            parent=self.dialog_parent
        )
        self.on_closing()

    def check_file_name(self, file_path):
        """
        Checks if the file name matches the required naming convention.
        If not, prompts the user to rename the file.
        """
        filename = os.path.basename(file_path)
        base_name, extension = os.path.splitext(filename)

        # if the file is a json file do not check the naming convention
        if extension.lower() == '.json':
            logging.info(f"File '{filename}' is a JSON file.")
            return

        # if the file is not a tiff file, alert the user and move the file to a 'rename' folder
        if extension.lower() != '.tiff':
            logging.info(f"File '{filename}' is not a TIFF file.")
            self.move_to_rename_folder(file_path, filename)
            return

        if not pattern.match(base_name):
            logging.info(f"File '{filename}' does not match the naming convention.")
            self.prompt_rename(file_path, filename)

        # if the file name already exists in the processed directory, get a unique name
        else:
            new_path = self.get_unique_path(self.processed_dir, filename)
            if new_path != file_path:
                os.rename(file_path, new_path)
                logging.info(f"File '{filename}' moved to '{new_path}'.")

    def prompt_rename(self, file_path, filename):
        """
        Prompts the user to rename the file using a graphical dialog.
        If the user cancels, moves the file to a 'rename' folder.
        """
        message = (
            f"The file '{filename}' does not adhere to the naming convention.\n"
            f"The required naming format is: Name_Institute_DataQualifier (e.g., MuS_IPAT_Sample-Name)",
        )

        messagebox.showwarning("Invalid File Name", message, parent=self.dialog_parent)

        while True:
            dialog = MultiFieldDialog(self.root, "Rename File")
            if dialog.result is None:
                # User cancelled the dialog
                self.move_to_rename_folder(file_path, filename)
                return

            name = dialog.result['name']
            institute = dialog.result['institute']
            data_qualifier = dialog.result['data_qualifier']

            # Check that none of the fields are empty
            if not name or not institute or not data_qualifier:
                messagebox.showwarning(
                    "Incomplete Information",
                    "All fields are required. Please fill in all fields.",
                    parent=self.dialog_parent
                )
                continue

            # Remove spaces and special characters to ensure the filename is valid
            name = re.sub(r'\W+', '', name)
            institute = re.sub(r'\W+', '', institute)
            data_qualifier = re.sub(r'[^\w-]+', '', data_qualifier)

            # Generate date string
            date_str = datetime.datetime.now().strftime('%Y%m%d')
            # Construct the new base name
            new_base_name = f"{self.device_name}_{name}_{institute}_{data_qualifier}_{date_str}"

            # Now, check if new_base_name matches the pattern
            if pattern.match(new_base_name):
                new_name = new_base_name + os.path.splitext(filename)[1]
                break
            else:
                messagebox.showwarning(
                    "Invalid File Name",
                    "The new file name does not match the required format or contains invalid characters. Please try again.",
                    parent=self.dialog_parent
                )

        self.rename_file(file_path, new_name)

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

        new_path = self.get_unique_path(rename_folder, new_filename)

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

    def rename_file(self, file_path, new_name):
        """
        Renames the file to the new name provided by the user.
        """
        new_path = self.get_unique_path(self.processed_dir, new_name)

        try:
            os.rename(file_path, new_path)
            messagebox.showinfo("Success", f"File renamed to '{os.path.basename(new_path)}'", parent=self.dialog_parent)
            logging.info(f"File '{file_path}' renamed to '{new_path}'.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to rename file: {e}", parent=self.dialog_parent)
            logging.error(f"Failed to rename file '{file_path}' to '{new_path}': {e}")

    def get_unique_path(self, directory, filename):
        """
        Generates a unique file path to avoid overwriting existing files.
        """
        base_name, extension = os.path.splitext(filename)
        counter = 1
        new_filename = filename
        new_path = os.path.join(directory, new_filename)

        while os.path.exists(new_path):
            new_filename = f"{base_name}_{counter}{extension}"
            new_path = os.path.join(directory, new_filename)
            counter += 1

        return new_path

    def process_events(self):
        """
        Processes file events from the queue.
        """
        while not self.event_queue.empty():
            file_path = self.event_queue.get()
            self.check_file_name(file_path)
        self.root.after(100, self.process_events)

    def on_closing(self):
        """
        Handles the application closing event.
        """
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
    path_to_watch = r"test_monitor"
    rename_folder = os.path.join(path_to_watch, 'To_Rename')
    processed_dir = r"test_monitor\Validated"
    app = FileMonitorApp(path_to_watch, device_name="SEM", processed_dir=processed_dir, rename_folder=rename_folder)
    app.run()
