import re
# Import the 're' module for regular expression operations.

import os
# Import the 'os' module to interact with the operating system's file system.

import time
# Import the 'time' module to pause execution in the main loop.

from watchdog.observers import Observer
# Import the 'Observer' class from the 'watchdog.observers' module.
# The Observer watches for file system events and dispatches them to event handlers.

from watchdog.events import FileSystemEventHandler
# Import the 'FileSystemEventHandler' class to create custom event handlers.

import tkinter as tk
from tkinter import simpledialog, messagebox
# Import Tkinter modules for creating graphical user interface dialogs.

# Define the regular expression pattern for the required file naming convention.
# The naming convention is: Name_Institute_Date_DataQualifier
# For example: 20241018_JFi_IPAT_DataSet1
pattern = re.compile(r'^\d{8}_[A-Za-z]+_[A-Za-z]+_[A-Za-z0-9]+$')
# This pattern matches names like "YYYYMMDD_Name_Institute_DataQualifier"

class FileNamingHandler(FileSystemEventHandler):
    # Create a subclass of 'FileSystemEventHandler' to define custom behavior when file system events occur.

    def on_created(self, event):
        """
        This method is automatically called by the observer when a new file or directory is created in the monitored path.
        The 'event' parameter contains information about the event, such as the file path.
        """
        if not event.is_directory:
            # Check if the created item is not a directory (i.e., it is a file).
            self.check_file_name(event.src_path)
            # Call the method to check if the new file's name adheres to the naming convention.

    def check_file_name(self, file_path):
        """
        Checks if the file name matches the required naming convention.
        If not, it prompts the user to rename the file.
        """
        filename = os.path.basename(file_path)
        # Extract the file name from the full file path.

        if not pattern.match(filename):
            # Use the regular expression 'pattern' to check if the file name matches the required naming convention.
            # If it doesn't match, proceed to prompt the user to rename the file.
            self.prompt_rename(file_path, filename)

    def prompt_rename(self, file_path, filename):
        """
        Prompts the user to rename the file using a graphical dialog.
        """
        root = tk.Tk()
        root.withdraw()  # Hide the root window.
        # Initialize Tkinter and hide the main window since we only need to display dialogs.

        # Prepare a warning message to inform the user about the invalid file name.
        message = f"The file '{filename}' does not adhere to the naming convention."

        # Display a warning message box to the user.
        messagebox.showwarning("Invalid File Name", message)

        # Prompt the user to enter a new file name, with the current file name as the default value.
        new_name = simpledialog.askstring("Rename File", "Enter a new file name:", initialvalue=filename)

        if new_name:
            # If the user provides a new name and doesn't cancel the dialog.
            dir_path = os.path.dirname(file_path)
            # Get the directory path of the file.

            new_path = os.path.join(dir_path, new_name)
            # Construct the full file path with the new file name.

            try:
                os.rename(file_path, new_path)
                # Attempt to rename the file to the new name.

                # Inform the user that the file has been successfully renamed.
                messagebox.showinfo("Success", f"File renamed to '{new_name}'")
            except Exception as e:
                # If an error occurs during renaming, catch the exception.
                messagebox.showerror("Error", f"Failed to rename file: {e}")
                # Display an error message to the user with the exception details.

        root.destroy()
        # Destroy the Tkinter root window to clean up resources.

if __name__ == "__main__":
    # This block will only execute if the script is run directly.

    path_to_watch = r"D:/Monitored_Folders/SEM"
    # Specify the path of the directory to be monitored.

    event_handler = FileNamingHandler()
    # Create an instance of the custom event handler.

    observer = Observer()
    # Create an Observer object to monitor the file system.

    observer.schedule(event_handler, path=path_to_watch, recursive=False)
    # Schedule the observer to monitor the specified path with the event handler.
    # Set 'recursive=True' if you want to monitor subdirectories as well.

    observer.start()
    # Start the observer thread, which will now monitor the directory for events.

    print(f"Monitoring directory: {path_to_watch}")
    # Inform the user that monitoring has started.

    try:
        while True:
            time.sleep(1)
            # Keep the script running indefinitely.
    except KeyboardInterrupt:
        # If the user presses Ctrl+C, stop the observer.
        observer.stop()
        print("Monitoring stopped.")

    observer.join()
    # Wait for the observer thread to finish before exiting.