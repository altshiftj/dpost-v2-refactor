import re
import os
import queue
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import tkinter as tk
from tkinter import simpledialog, messagebox
from tkinter import Toplevel, Label, Entry, Button
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define the regular expression pattern for the required file naming convention.
pattern = re.compile(r'^[A-Za-z0-9]+_[A-Za-z]+_[A-Za-z]+_[A-Za-z0-9]+_\d{8}$')

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

class FileMonitorApp:
    """
    Main application class that monitors a directory and ensures files adhere to a naming convention.
    """
    def __init__(self, path_to_watch, device_name):
        self.path_to_watch = path_to_watch
        self.device_name = device_name

        # Initialize Tkinter root
        self.root = tk.Tk()
        self.root.withdraw()  # Hide the root window

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

    def check_file_name(self, file_path):
        """
        Checks if the file name matches the required naming convention.
        If not, prompts the user to rename the file.
        """
        filename = os.path.basename(file_path)
        base_name, extension = os.path.splitext(filename)

        if not pattern.match(base_name):
            logging.info(f"File '{filename}' does not match the naming convention.")
            self.prompt_rename(file_path, filename)

    def prompt_rename(self, file_path, filename):
        """
        Prompts the user to rename the file using a graphical dialog.
        If the user cancels, moves the file to a 'rename' folder.
        """
        message = (
            f"The file '{filename}' does not adhere to the naming convention.\n"
            f"The required naming format is: device_name_institute_data-qualifier_date (e.g., Name_Institute_Data-Qualifier)"
        )

        messagebox.showwarning("Invalid File Name", message)

        base_name, extension = os.path.splitext(filename)
        new_name = base_name

        
        rename_window = Toplevel(self.root)
        rename_window.title("Rename File")

        Label(rename_window, text="Enter Initials: \n Ex: MuS").grid(row=0, column=0, padx=10, pady=5)
        name_entry = Entry(rename_window)
        name_entry.grid(row=0, column=1, padx=10, pady=5)

        Label(rename_window, text="Enter Institute: \n Ex: IPAT").grid(row=1, column=0, padx=10, pady=5)
        institute_entry = Entry(rename_window)
        institute_entry.grid(row=1, column=1, padx=10, pady=5)

        Label(rename_window, text="Enter Data Qualifier: \n Cathode-90s").grid(row=2, column=0, padx=10, pady=5)
        data_qualifier_entry = Entry(rename_window)
        data_qualifier_entry.grid(row=2, column=1, padx=10, pady=5)

        def on_submit():
            name = name_entry.get()
            institute = institute_entry.get()
            data_qualifier = data_qualifier_entry.get()

            if not name or not institute or not data_qualifier:
                self.move_to_rename_folder(file_path, filename)
                rename_window.destroy()
                return

            # Extract the creation date of the file
            creation_time = os.path.getctime(file_path)
            creation_date = datetime.fromtimestamp(creation_time).strftime('%Y%m%d')

            # Construct the new file name
            base_name, extension = os.path.splitext(filename)
            new_base_name = f"{self.device_name}_{name}_{institute}_{data_qualifier}_{creation_date}"
            new_name = f"{new_base_name}{extension}"

            if pattern.match(new_base_name):
                # Valid new name provided
                self.rename_file(file_path, new_name)
                rename_window.destroy()
            else:
                messagebox.showwarning(
                    "Invalid File Name",
                    "The new file name does not match the required format. Please try again."
                )

        submit_button = Button(rename_window, text="Submit", command=on_submit)
        submit_button.grid(row=3, column=0, columnspan=2, pady=10)

    def move_to_rename_folder(self, file_path, filename):
        """
        Moves the file to a 'rename' folder if the user cancels the renaming process.
        """
        dir_path = os.path.dirname(file_path)
        rename_folder = os.path.join(dir_path, 'rename')

        if not os.path.exists(rename_folder):
            try:
                os.makedirs(rename_folder)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create 'rename' folder: {e}")
                return

        new_path = self.get_unique_path(rename_folder, filename)

        try:
            os.rename(file_path, new_path)
            messagebox.showinfo(
                "File Moved",
                f"File renaming was cancelled. The file has been moved to: {new_path}"
            )
            logging.info(f"File moved to '{new_path}'.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to move file: {e}")
            logging.error(f"Failed to move file '{file_path}' to '{new_path}': {e}")

    def rename_file(self, file_path, new_name):
        """
        Renames the file to the new name provided by the user.
        """
        dir_path = os.path.dirname(file_path)
        new_path = self.get_unique_path(dir_path, new_name)

        try:
            os.rename(file_path, new_path)
            messagebox.showinfo("Success", f"File renamed to '{os.path.basename(new_path)}'")
            logging.info(f"File '{file_path}' renamed to '{new_path}'.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to rename file: {e}")
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

if __name__ == "__main__":
    path_to_watch = r"D:/Monitored_Folders/SEM"
    device_name = "Device123"  # Example device name, you can adjust as needed
    app = FileMonitorApp(path_to_watch, device_name)
    app.run()
