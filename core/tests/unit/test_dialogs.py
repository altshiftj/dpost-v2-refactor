import pytest
import tkinter as tk
from unittest.mock import patch, MagicMock
from core.ui.dialogs import EntryWithPlaceholder, RenameDialog
from core.ui.ui_messages import DialogPrompts


# -----------------------------------------------------------------------------
# Fixtures and Utilities
# -----------------------------------------------------------------------------


@pytest.fixture(scope="module")
def tk_root():
    root = tk.Tk()
    root.withdraw()
    yield root
    root.destroy()


class DummyUI:
    def __init__(self):
        self.calls = {
            "show_warning": [],
            "show_info": [],
            "show_error": [],
            "prompt_rename": [],
            "prompt_append_record": [],
            "show_rename_dialog": [],
        }
        self.prompt_rename_return = None
        self.prompt_append_record_return = None
        self.show_rename_dialog_return = None

    def show_warning(self, title, message):
        self.calls["show_warning"].append((title, message))

    def show_info(self, title, message):
        self.calls["show_info"].append((title, message))

    def show_error(self, title, message):
        self.calls["show_error"].append((title, message))

    def prompt_rename(self):
        self.calls["prompt_rename"].append("called")
        return self.prompt_rename_return

    def show_rename_dialog(self, attempted, analysis):
        self.calls["show_rename_dialog"].append((attempted, analysis))
        return self.show_rename_dialog_return

    def prompt_append_record(self, record_name):
        self.calls["prompt_append_record"].append(record_name)
        return self.prompt_append_record_return

    def schedule_task(self, interval_ms, callback):
        callback()
        return 1

    def cancel_task(self, handle):
        pass

    def set_close_handler(self, callback):
        self.close_handler = callback

    def set_exception_handler(self, callback):
        self.exception_handler = callback

    def get_root(self):
        root = tk.Tk()
        root.withdraw()
        return root


# -----------------------------------------------------------------------------
# Tests for EntryWithPlaceholder
# -----------------------------------------------------------------------------


def test_entry_with_placeholder_shows_initial_placeholder(tk_root):
    entry = EntryWithPlaceholder(tk_root, placeholder="Enter text here")
    assert entry.get() == "", "Should return empty string if placeholder is active"
    assert entry.get() == ""


def test_entry_with_placeholder_on_key_press(tk_root):
    entry = EntryWithPlaceholder(tk_root, placeholder="Email")
    entry._on_key_pressed(event=MagicMock())  # Simulate key press
    entry.insert(0, "x")  # Manually simulate input
    assert entry.get() == "x"


def test_entry_with_placeholder_focus_out_restores_placeholder(tk_root):
    entry = EntryWithPlaceholder(tk_root, placeholder="Name")
    entry._on_key_pressed(event=MagicMock())  # Clear placeholder
    entry.delete(0, tk.END)  # Simulate user clearing input
    entry._on_focus_out(event=MagicMock())  # Simulate focus loss
    assert entry.get() == ""


def test_entry_with_placeholder_set_and_get(tk_root):
    entry = EntryWithPlaceholder(tk_root, placeholder="Location")
    entry.set("Test Value")
    assert entry.get() == "Test Value"
    entry.set("")
    assert entry.get() == ""


# -----------------------------------------------------------------------------
# Tests for RenameDialog
# -----------------------------------------------------------------------------


@pytest.fixture
def rename_dialog_setup(tk_root):
    def _build_dialog(attempted_filename="Bad--Name", violation_info=None):
        if violation_info is None:
            violation_info = {
                "valid": False,
                "reasons": ["Invalid format"],
                "highlight_spans": [(0, 3)],
            }
        # Patch modal dialog behavior
        with patch("tkinter.simpledialog.Dialog.wait_window"), patch(
            "tkinter.simpledialog.Dialog.grab_set"
        ):
            dialog = RenameDialog(tk_root, attempted_filename, violation_info)
        return dialog

    return _build_dialog


def test_rename_dialog_creation(rename_dialog_setup):
    dialog = rename_dialog_setup()
    assert dialog.attempted_filename == "Bad--Name"
    assert not dialog.violation_info["valid"]
    assert dialog.title() == DialogPrompts.RENAME_FILE


def test_rename_dialog_validate_blocks_empty_fields(rename_dialog_setup):
    dialog = rename_dialog_setup()
    dialog.user_entry.delete(0, tk.END)
    dialog.institute_entry.delete(0, tk.END)
    dialog.sample_entry.delete(0, tk.END)

    with patch("tkinter.messagebox.showerror") as mock_error:
        is_valid = dialog.validate()
        assert not is_valid
        mock_error.assert_called_once()


def test_rename_dialog_apply_sets_result(rename_dialog_setup):
    dialog = rename_dialog_setup()
    dialog.user_entry.insert(0, "User")
    dialog.institute_entry.insert(0, "Lab")
    dialog.sample_entry.insert(0, "Sample123")

    with patch.object(dialog, "validate", return_value=True):
        dialog.apply()
        assert dialog.result == {
            "name": "User",
            "institute": "Lab",
            "sample_ID": "Sample123",
        }


def test_rename_dialog_ok_flow(rename_dialog_setup):
    dialog = rename_dialog_setup()
    dialog.user_entry.insert(0, "U")
    dialog.institute_entry.insert(0, "I")
    dialog.sample_entry.insert(0, "S")

    with patch.object(dialog, "validate", return_value=True), patch.object(
        dialog, "withdraw"
    ), patch.object(dialog, "update_idletasks"):
        dialog.ok()
    assert dialog.result == {"name": "U", "institute": "I", "sample_ID": "S"}


def test_rename_dialog_cancel_flow(rename_dialog_setup):
    dialog = rename_dialog_setup()
    with patch.object(dialog, "withdraw"), patch.object(dialog, "update_idletasks"):
        dialog.cancel()
    assert dialog.result is None
