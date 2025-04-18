import pytest
from unittest.mock import patch, MagicMock

import tkinter.messagebox as messagebox
from ipat_watchdog.ui.ui_tkinter import TKinterUI
from ipat_watchdog.ui.ui_messages import DialogPrompts, InfoMessages


@pytest.fixture
def ui_instance():
    with patch("tkinter.Tk") as MockTk, patch("tkinter.Toplevel") as MockTop:
        mock_root = MockTk.return_value
        mock_top = MockTop.return_value
        ui = TKinterUI()
        return ui


def test_show_warning(ui_instance):
    with patch.object(messagebox, "showwarning") as mock_warn:
        ui_instance.show_warning("Oops", "Something's off")
        mock_warn.assert_called_once_with(
            "Oops", "Something's off", parent=ui_instance.dialog_parent
        )


def test_show_info(ui_instance):
    with patch.object(messagebox, "showinfo") as mock_info:
        ui_instance.show_info("FYI", "Hello there")
        mock_info.assert_called_once_with(
            "FYI", "Hello there", parent=ui_instance.dialog_parent
        )


def test_show_error(ui_instance):
    with patch.object(messagebox, "showerror") as mock_error:
        ui_instance.show_error("Boom", "Explosion happened")
        mock_error.assert_called_once_with(
            "Boom", "Explosion happened", parent=ui_instance.dialog_parent
        )


def test_show_rename_dialog(ui_instance):
    with patch("ipat_watchdog.ui.ui_tkinter.RenameDialog") as MockDialog:
        MockDialog.return_value.result = {
            "name": "alice",
            "institute": "lab",
            "sample_ID": "abc123",
        }
        result = ui_instance.show_rename_dialog("alice-lab-abc123", {"valid": False})
        assert result == {"name": "alice", "institute": "lab", "sample_ID": "abc123"}


def test_prompt_append_record(ui_instance):
    with patch.object(messagebox, "askyesno", return_value=True) as mock_ask:
        result = ui_instance.prompt_append_record("rec1")
        mock_ask.assert_called_once_with(
            DialogPrompts.APPEND_RECORD,
            DialogPrompts.APPEND_RECORD_DETAILS.format(record_name="rec1"),
            parent=ui_instance.dialog_parent,
        )
        assert result is True


def test_schedule_and_cancel_task(ui_instance):
    mock_callback = MagicMock()
    ui_instance.root.after.return_value = "task-id-1"

    handle = ui_instance.schedule_task(250, mock_callback)
    assert handle == "task-id-1"

    ui_instance.cancel_task(handle)
    ui_instance.root.after_cancel.assert_called_once_with("task-id-1")


def test_set_close_handler(ui_instance):
    cb = MagicMock()
    ui_instance.set_close_handler(cb)
    ui_instance.root.protocol.assert_called_once_with("WM_DELETE_WINDOW", cb)


def test_set_exception_handler(ui_instance):
    handler = MagicMock()
    ui_instance.set_exception_handler(handler)
    assert ui_instance.root.report_callback_exception == handler


def test_get_root(ui_instance):
    assert ui_instance.get_root() == ui_instance.root


def test_destroy(ui_instance):
    mock_dialog = MagicMock()
    mock_dialog.winfo_exists.return_value = True
    ui_instance._active_dialogs["test_dialog"] = mock_dialog

    ui_instance.dialog_parent.winfo_exists.return_value = True
    ui_instance.root.winfo_exists.return_value = True

    ui_instance.destroy()

    mock_dialog.destroy.assert_called_once()
    ui_instance.dialog_parent.destroy.assert_called_once()
    ui_instance.root.destroy.assert_called_once()
