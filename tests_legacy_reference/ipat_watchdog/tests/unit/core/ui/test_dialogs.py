import pytest
from unittest.mock import patch, MagicMock
from ipat_watchdog.core.ui.dialogs import EntryWithPlaceholder, RenameDialog
from ipat_watchdog.core.interactions.messages import DialogPrompts


# ---------------------------------------------------------------------
# EntryWithPlaceholder Tests
# ---------------------------------------------------------------------


def test_entry_with_placeholder_shows_initial_placeholder(fake_ui):
    entry = EntryWithPlaceholder(fake_ui.get_root(), placeholder="Enter text here")
    assert entry.get() == "", "Should return empty string if placeholder is active"


def test_entry_with_placeholder_on_key_press(fake_ui):
    entry = EntryWithPlaceholder(fake_ui.get_root(), placeholder="Email")
    entry._on_key_pressed(event=MagicMock())  # Simulate key press
    entry.insert(0, "x")  # Simulate user typing
    assert entry.get() == "x"


def test_entry_with_placeholder_focus_out_restores_placeholder(fake_ui):
    entry = EntryWithPlaceholder(fake_ui.get_root(), placeholder="Name")
    entry._on_key_pressed(event=MagicMock())
    entry.delete(0, "end")
    entry._on_focus_out(event=MagicMock())
    assert entry.get() == ""


def test_entry_with_placeholder_set_and_get(fake_ui):
    entry = EntryWithPlaceholder(fake_ui.get_root(), placeholder="Location")
    entry.set("Test Value")
    assert entry.get() == "Test Value"
    entry.set("")
    assert entry.get() == ""


# ---------------------------------------------------------------------
# RenameDialog Tests
# ---------------------------------------------------------------------


@pytest.fixture
def rename_dialog_setup(fake_ui):
    def _build_dialog(attempted_filename="Bad--Name", violation_info=None):
        if violation_info is None:
            violation_info = {
                "valid": False,
                "reasons": ["Invalid format"],
                "highlight_spans": [(0, 3)],
            }

        with patch("tkinter.simpledialog.Dialog.wait_window"), patch(
            "tkinter.simpledialog.Dialog.grab_set"
        ):
            dialog = RenameDialog(fake_ui.get_root(), attempted_filename, violation_info)
        return dialog

    return _build_dialog


def test_rename_dialog_creation(rename_dialog_setup):
    dialog = rename_dialog_setup()
    assert dialog.attempted_filename == "Bad--Name"
    assert not dialog.violation_info["valid"]
    assert dialog.title() == DialogPrompts.RENAME_FILE


def test_rename_dialog_validate_blocks_empty_fields(rename_dialog_setup):
    dialog = rename_dialog_setup()
    dialog.user_entry.delete(0, "end")
    dialog.institute_entry.delete(0, "end")
    dialog.sample_entry.delete(0, "end")

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
