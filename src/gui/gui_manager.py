import tkinter as tk
from tkinter import messagebox
from abc import ABC, abstractmethod

from src.gui.dialogs import MultiFieldDialog
from src.sessions.session_manager import SessionManager

class UserInterface(ABC):
    @abstractmethod
    def show_warning(self, title: str, message: str):
        pass

    @abstractmethod
    def show_info(self, title: str, message: str):
        pass

    @abstractmethod
    def prompt_rename(self):
        """
        Returns a dict with user responses like:
        {"name": ..., "institute": ..., "sample_ID": ...} or None if canceled.
        """
        pass

    @abstractmethod
    def prompt_append_record(self, record_name: str) -> bool:
        pass

    @abstractmethod
    def show_error(self, title: str, message: str):
        pass

    @abstractmethod
    def show_done_dialog(self, session_manager):
        pass


# GuiManager manages all GUI-related interactions using Tkinter
class GUIManager(UserInterface):
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
        return messagebox.askyesno("Append to Existing Record", f"Record '{record_name}' was already created today. Add file to existing record?", parent=self.dialog_parent)

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
