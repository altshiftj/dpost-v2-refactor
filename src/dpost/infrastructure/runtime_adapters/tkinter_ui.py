"""Tkinter desktop UI adapter used by dpost runtime mode selection."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox
from typing import Any, Callable

from dpost.application.interactions import DialogPrompts, InfoMessages
from dpost.application.ports import SessionPromptDetails, UserInterface
from dpost.infrastructure.runtime_adapters.dialogs import RenameDialog


class TKinterRuntimeUI(UserInterface):
    """Concrete desktop runtime UI adapter backed by Tkinter."""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.withdraw()

        self.dialog_parent = tk.Toplevel(self.root)
        self.dialog_parent.withdraw()
        self.dialog_parent.attributes("-topmost", True)

        self._ui_thread_id = threading.get_ident()
        self._active_dialogs: dict[str, tk.Toplevel] = {}

    def initialize(self) -> None:
        """Initialize desktop UI state."""

    def show_warning(self, title: str, message: str) -> None:
        messagebox.showwarning(title, message, parent=self.dialog_parent)

    def show_info(self, title: str, message: str) -> None:
        messagebox.showinfo(title, message, parent=self.dialog_parent)

    def show_error(self, title: str, message: str) -> None:
        messagebox.showerror(title, message, parent=self.dialog_parent)

    def prompt_rename(self) -> dict[str, str] | None:
        dialog = RenameDialog(self.root, "", {})
        return dialog.result

    def show_rename_dialog(
        self, attempted_filename: str, analysis: dict[str, object]
    ) -> dict[str, str] | None:
        def _open_dialog() -> dict[str, str] | None:
            dialog = RenameDialog(self.get_root(), attempted_filename, analysis)
            return dialog.result

        return self.run_on_ui_sync(_open_dialog)

    def prompt_append_record(self, record_name: str) -> bool:
        return messagebox.askyesno(
            DialogPrompts.APPEND_RECORD,
            DialogPrompts.APPEND_RECORD_DETAILS.format(record_name=record_name),
            parent=self.dialog_parent,
        )

    def show_done_dialog(
        self,
        session_details: SessionPromptDetails,
        on_done_callback: Callable[[], None],
    ) -> None:
        if (
            "done_dialog" in self._active_dialogs
            and self._active_dialogs["done_dialog"].winfo_exists()
        ):
            self._active_dialogs["done_dialog"].destroy()

        done_dialog = tk.Toplevel(self.root)
        done_dialog.title(InfoMessages.SESSION_ACTIVE)
        done_dialog.attributes("-topmost", True)
        done_dialog.resizable(False, False)

        label = tk.Label(
            done_dialog,
            text=self._compose_session_message(session_details),
            justify=tk.LEFT,
            anchor="w",
        )
        label.pack(padx=20, pady=10, fill="both")

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
        done_dialog.protocol("WM_DELETE_WINDOW", lambda: None)
        self._active_dialogs["done_dialog"] = done_dialog

    def get_root(self) -> tk.Tk:
        return self.root

    def destroy(self) -> None:
        for dialog in self._active_dialogs.values():
            if dialog.winfo_exists():
                dialog.destroy()
        self._active_dialogs.clear()

        if self.dialog_parent.winfo_exists():
            self.dialog_parent.destroy()
        if self.root.winfo_exists():
            self.root.destroy()

    def schedule_task(self, interval_ms: int, callback: Callable[[], None]) -> str:
        return self.root.after(interval_ms, callback)

    def cancel_task(self, handle: Any) -> None:
        if handle is None:
            return
        try:
            self.root.after_cancel(handle)
        except ValueError:
            return

    def set_close_handler(self, callback: Callable[[], None]) -> None:
        self.root.protocol("WM_DELETE_WINDOW", callback)

    def set_exception_handler(self, callback: Callable[..., None]) -> None:
        self.root.report_callback_exception = callback

    def run_main_loop(self) -> None:
        self.root.mainloop()

    def is_ui_thread(self) -> bool:
        """Return whether current execution is already on the Tk thread."""
        return threading.get_ident() == self._ui_thread_id

    def run_on_ui(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        """Schedule callable to run asynchronously on the Tk thread."""
        self.get_root().after(0, lambda: fn(*args, **kwargs))

    def run_on_ui_sync(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute callable on Tk thread and block until result is available."""
        if self.is_ui_thread():
            return fn(*args, **kwargs)

        done = threading.Event()
        output: dict[str, Any] = {"value": None, "exc": None}

        def runner() -> None:
            try:
                output["value"] = fn(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001
                output["exc"] = exc
            finally:
                done.set()

        self.get_root().after(0, runner)
        done.wait()
        if output["exc"] is not None:
            raise output["exc"]
        return output["value"]

    def _compose_session_message(self, details: SessionPromptDetails) -> str:
        lines = [InfoMessages.SESSION_ACTIVE_DETAILS]
        if details.users:
            lines.append("")
            lines.append("Users in session:")
            lines.extend(f"  - {user}" for user in details.users)
        if details.records:
            lines.append("")
            lines.append("Records processed in this session:")
            lines.extend(f"  - {record}" for record in details.records)
        return "\n".join(lines)

    def _handle_done_clicked(
        self, dialog: tk.Toplevel, callback: Callable[[], None]
    ) -> None:
        if dialog.winfo_exists():
            dialog.destroy()
        if "done_dialog" in self._active_dialogs:
            del self._active_dialogs["done_dialog"]
        callback()
