"""
This module defines classes for handling all GUI-related interactions.
It provides an abstract base class (UserInterface) that outlines required GUI methods,
and a concrete implementation (TKinterUI) that displays dialogs, pop-ups, and other
UI elements to guide user interactions.
"""

import tkinter as tk
from tkinter import messagebox
from typing import Dict, Optional, Callable, Any
import threading

from ipat_watchdog.core.ui.ui_abstract import UserInterface
from ipat_watchdog.core.ui.dialogs import RenameDialog
from ipat_watchdog.core.interactions.messages import InfoMessages, DialogPrompts


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
        dialog parent window (self.dialog_parent).
        """
        # Create a root Tkinter window and immediately hide it
        self.root = tk.Tk()
        self.root.withdraw()

        # Create a separate dialog parent to ensure messageboxes and dialogs
        # appear on top of the main application window
        self.dialog_parent = tk.Toplevel(self.root)
        self.dialog_parent.withdraw()
        self.dialog_parent.attributes("-topmost", True)

        # Record the UI thread id for marshaling work onto Tk thread
        self._ui_thread_id = threading.get_ident()

        # Dictionary to track active dialogs by type
        self._active_dialogs = {}

    # -------------------------------------------------------------------------
    # Required Methods per UserInterface
    # -------------------------------------------------------------------------

    def initialize(self) -> None:
        """
        Perform any additional initialization required for the UI.
        For TKinter, most is done in __init__, but this method
        can be used for post-construction setup if needed.
        """
        pass

    def show_warning(self, title: str, message: str) -> None:
        messagebox.showwarning(title, message, parent=self.dialog_parent)

    def show_info(self, title: str, message: str) -> None:
        messagebox.showinfo(title, message, parent=self.dialog_parent)

    def show_error(self, title: str, message: str) -> None:
        messagebox.showerror(title, message, parent=self.dialog_parent)

    def prompt_rename(self) -> Optional[Dict[str, str]]:
        """
        Display a dialog prompting the user to rename a file or folder.
        Returns a dict with user input if confirmed, or None if canceled.
        """
        dialog = RenameDialog(self.root, "Rename File")
        return dialog.result

    def show_rename_dialog(
        self, attempted_filename: str, analysis: dict
    ) -> Optional[dict]:
        """Open the rename dialog on the Tk thread and return the user input dict or None."""
        def _open():
            dialog = RenameDialog(self.get_root(), attempted_filename, analysis)
            return dialog.result
        return self.run_on_ui_sync(_open)

    def prompt_append_record(self, record_name: str) -> bool:
        """
        Ask user if they want to append new data to an existing record.
        """
        return messagebox.askyesno(
            DialogPrompts.APPEND_RECORD,
            DialogPrompts.APPEND_RECORD_DETAILS.format(record_name=record_name),
            parent=self.dialog_parent,
        )

    def show_done_dialog(self, on_done_callback: Callable[[], None]) -> None:
        """
        Show a pop-up dialog that prompts the user to confirm they are done.
        Calls 'on_done_callback' when user clicks 'Done'.
        """
        if (
            "done_dialog" in self._active_dialogs
            and self._active_dialogs["done_dialog"].winfo_exists()
        ):
            self._active_dialogs["done_dialog"].destroy()

        done_dialog = tk.Toplevel(self.root)
        done_dialog.title(InfoMessages.SESSION_ACTIVE)
        done_dialog.attributes("-topmost", True)

        label = tk.Label(done_dialog, text=InfoMessages.SESSION_ACTIVE_DETAILS)
        label.pack(padx=20, pady=10)

        if not callable(on_done_callback):
            raise TypeError(
                f"on_done_callback must be callable, got {type(on_done_callback)}"
            )

        done_button = tk.Button(
            done_dialog,
            text="Done",
            command=lambda: self._handle_done_clicked(done_dialog, on_done_callback),
        )
        done_button.pack(pady=10)

        # Disable 'X' button by overriding close protocol with a no-op
        done_dialog.protocol("WM_DELETE_WINDOW", lambda: None)
        
        self._active_dialogs["done_dialog"] = done_dialog

    def get_root(self) -> tk.Tk:
        """
        Return the underlying Tk root window.
        """
        return self.root

    def destroy(self) -> None:
        """
        Destroy and clean up all UI resources, closing any windows/dialogs.
        """
        # Close any active dialogs
        for dialog in self._active_dialogs.values():
            if dialog.winfo_exists():
                dialog.destroy()
        self._active_dialogs.clear()

        if self.dialog_parent.winfo_exists():
            self.dialog_parent.destroy()
        if self.root.winfo_exists():
            self.root.destroy()

    def schedule_task(self, interval_ms: int, callback: Callable[[], None]) -> int:
        """
        Schedule a callback to run once after 'interval_ms' milliseconds.
        Returns an ID (string) that can be used to cancel the task.
        """
        return self.root.after(interval_ms, callback)

    def cancel_task(self, handle: int) -> None:
        """
        Cancel a previously scheduled task identified by 'handle'.
        """
        if handle is not None:
            try:
                self.root.after_cancel(handle)
            except ValueError:
                # If handle is invalid or already canceled, ignore
                pass

    def set_close_handler(self, callback: Callable[[], None]) -> None:
        """
        Set a callback to be invoked if the user attempts to close the main window.
        """
        self.root.protocol("WM_DELETE_WINDOW", callback)

    def set_exception_handler(self, callback: Callable[..., None]) -> None:
        """
        Set a global exception handler for the UI environment.
        """
        self.root.report_callback_exception = callback

    def run_main_loop(self) -> None:
        """
        Enter the Tkinter main event loop.
        """
        self.root.mainloop()

    # -------------------------------------------------------------------------
    # UI Thread helpers
    # -------------------------------------------------------------------------

    def is_ui_thread(self) -> bool:
        """Return True if current code is running on the Tk thread."""
        return threading.get_ident() == self._ui_thread_id

    def run_on_ui(self, fn: Callable[..., Any], *args, **kwargs) -> None:
        """Schedule fn to run on the Tk thread asynchronously."""
        self.get_root().after(0, lambda: fn(*args, **kwargs))

    def run_on_ui_sync(self, fn: Callable[..., Any], *args, **kwargs):
        """Run fn on the Tk thread synchronously and return its result."""
        if self.is_ui_thread():
            return fn(*args, **kwargs)

        done = threading.Event()
        out: dict[str, Any] = {"value": None, "exc": None}

        def runner():
            try:
                out["value"] = fn(*args, **kwargs)
            except Exception as e:  # noqa: BLE001 keep broad to bubble up
                out["exc"] = e
            finally:
                done.set()

        self.get_root().after(0, runner)
        done.wait()
        if out["exc"] is not None:
            raise out["exc"]
        return out["value"]

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _handle_done_clicked(
        self, dialog: tk.Toplevel, callback: Callable[[], None]
    ) -> None:
        """
        Invoked when the user clicks the 'Done' button in the done_dialog.
        Destroys the dialog and triggers the callback.
        """
        if dialog.winfo_exists():
            dialog.destroy()
        if "done_dialog" in self._active_dialogs:
            del self._active_dialogs["done_dialog"]
        callback()

    def _close_dialog(self, dialog: tk.Toplevel) -> None:
        """
        Closes a dialog and removes it from the _active_dialogs tracker.
        """
        if dialog.winfo_exists():
            dialog.destroy()
        for key, tracked_dialog in list(self._active_dialogs.items()):
            if tracked_dialog == dialog:
                del self._active_dialogs[key]
                break
