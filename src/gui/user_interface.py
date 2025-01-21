"""
gui_manager.py

This module defines classes for handling all GUI-related interactions.
It provides an abstract base class (UserInterface) that outlines required GUI methods,
and a concrete implementation (TKinterUI) that displays dialogs, pop-ups, and other
UI elements to guide user interactions. 
"""

import tkinter as tk
from tkinter import messagebox
from abc import ABC, abstractmethod

from src.gui.dialogs import MultiFieldDialog
from src.sessions.session_manager import SessionManager

class UserInterface(ABC):
    """
    An abstract base class that defines the methods every GUI manager must implement.
    It describes the interface for showing messages, warnings, error dialogs,
    and prompting user input.
    """

    @abstractmethod
    def show_warning(self, title: str, message: str):
        """
        Displays a warning message to the user.

        :param title: The title of the warning dialog.
        :param message: The message content to display.
        """
        pass

    @abstractmethod
    def show_info(self, title: str, message: str):
        """
        Displays an informational message to the user.

        :param title: The title of the info dialog.
        :param message: The message content to display.
        """
        pass

    @abstractmethod
    def prompt_rename(self):
        """
        Prompts the user for a new name for a file or folder that does not match
        the naming convention. 

        :return: A dictionary containing the user responses, e.g.,
                 {"name": ..., "institute": ..., "sample_ID": ...}
                 or None if the user canceled the dialog.
        """
        pass

    @abstractmethod
    def prompt_append_record(self, record_name: str) -> bool:
        """
        Asks the user whether they want to append new data to an already existing,
        uploaded record.

        :param record_name: The short ID of the record.
        :return: True if the user opts to append to the existing record, False otherwise.
        """
        pass

    @abstractmethod
    def show_error(self, title: str, message: str):
        """
        Displays an error message to the user.

        :param title: The title of the error dialog.
        :param message: The error message to display.
        """
        pass

    @abstractmethod
    def show_done_dialog(self, session_manager):
        """
        Displays a dialog that indicates a session is in progress, allowing the
        user to end the session when they are finished with their tasks.

        :param session_manager: An instance of SessionManager to handle session ending.
        """
        pass


class TKinterUI(UserInterface):
    """
    A concrete implementation of the UserInterface that manages all GUI interactions 
    using Tkinter. This includes displaying warnings, info popups, and error messages,
    as well as providing dialogs for renaming files/folders and confirming session-related
    actions.
    """

    def __init__(self):
        """
        Initializes the TKinterUI. Sets up a hidden root window (self.root) and a hidden
        dialog parent window (self.dialog_parent), both of which are used for displaying
        message boxes and custom dialogs on top of the main application.
        """
        # Create a root Tkinter window and immediately hide it
        self.root = tk.Tk()
        self.root.withdraw()

        # Create a separate dialog parent to ensure messageboxes and dialogs
        # appear on top of the main application window
        self.dialog_parent = tk.Toplevel(self.root)
        self.dialog_parent.withdraw()
        self.dialog_parent.attributes("-topmost", True)

    def show_warning(self, title, message):
        """
        Displays a warning message to the user as a pop-up dialog.

        :param title: The title of the warning dialog.
        :param message: The content (warning message) to show.
        """
        messagebox.showwarning(title, message, parent=self.dialog_parent)

    def show_info(self, title, message):
        """
        Displays an informational message to the user as a pop-up dialog.

        :param title: The title of the info dialog.
        :param message: The content (information) to show.
        """
        messagebox.showinfo(title, message, parent=self.dialog_parent)

    def show_error(self, title, message):
        """
        Displays an error message to the user as a pop-up dialog.

        :param title: The title of the error dialog.
        :param message: The content (error message) to show.
        """
        messagebox.showerror(title, message, parent=self.dialog_parent)

    def prompt_rename(self):
        """
        Opens a MultiFieldDialog for the user to enter new naming components 
        (e.g., user name, institute, sample name).

        :return: A dict containing user input (name, institute, sample_ID),
                 or None if the user canceled.
        """
        dialog = MultiFieldDialog(self.root, "Rename File")
        return dialog.result

    def prompt_append_record(self, record_name):
        """
        Asks the user via a yes/no dialog whether to append new files/folders
        to an existing record that was already uploaded.

        :param record_name: The short ID of the existing record.
        :return: True if the user clicks 'Yes', False if 'No'.
        """
        return messagebox.askyesno(
            "Append to Existing Record", 
<<<<<<< HEAD
            f"Record '{record_name}' was already created today. Add file to existing record?",
=======
            f"Record '{record_name}' already exists. Add file to existing record?",
>>>>>>> ref-sqlpersistence
            parent=self.dialog_parent
        )

    def show_done_dialog(self, session_manager: SessionManager):
        """
        Shows a dialog indicating that a session is currently active. The user
        can click "Done" to end the session. Ensures only one such dialog exists
        at a time.

        :param session_manager: SessionManager instance for ending the session.
        """
        # If the done_dialog already exists and is open, destroy it to avoid duplicates
        if hasattr(self, 'done_dialog') and self.done_dialog.winfo_exists():
            self.done_dialog.destroy()

        # Create a new top-level window for the session progress
        self.done_dialog = tk.Toplevel(self.root)
        self.done_dialog.title("Session Active")
        self.done_dialog.attributes("-topmost", True)

        # Display a label describing the active session
        label = tk.Label(
            self.done_dialog, 
            text="A session is in progress. Click 'Done' when finished."
        )
        label.pack(padx=20, pady=10)

        # Create a "Done" button that triggers the session to end
        done_button = tk.Button(
            self.done_dialog, 
            text="Done", 
            command=self._end_session_via_manager(session_manager)
        )
        done_button.pack(pady=10)

        # If user closes the window via the 'X' button, just destroy the dialog
        self.done_dialog.protocol("WM_DELETE_WINDOW", self._close_dialog)

    def _end_session_via_manager(self, session_manager: SessionManager):
        """
        Wraps the actual session ending logic to ensure any open 'done_dialog'
        window is destroyed first.

        :param session_manager: SessionManager instance for ending the session.
        :return: A function (closure) that can be called to end the session.
        """
        def wrapper():
            # Destroy the dialog if it's still open
            if self.done_dialog and self.done_dialog.winfo_exists():
                self.done_dialog.destroy()
            # Then end the session
            session_manager.end_session()
        return wrapper

    def _close_dialog(self):
        """
        Callback for when the user clicks the window's 'X' button on the 
        'done_dialog'. Closes the dialog if it's still active.
        """
        if self.done_dialog and self.done_dialog.winfo_exists():
            self.done_dialog.destroy()

    def destroy(self):
        """
        Destroys both the dialog_parent window and the root window, effectively 
        shutting down the Tkinter GUI. This is typically called when the application
        closes or the GUI is no longer needed.
        """
        self.dialog_parent.destroy()
        self.root.destroy()
