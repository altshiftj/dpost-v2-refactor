import pytest
from unittest.mock import patch, MagicMock
from watchdog.events import FileSystemEvent, DirCreatedEvent
from queue import Queue
from pathlib import Path

from ipat_watchdog.handlers.file_event_handler import FileEventHandler

# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def event_queue():
    """Fixture to provide an event queue for testing."""
    return Queue()


@pytest.fixture
def handler(event_queue, tmp_settings):
    """Fixture to provide the handler with settings."""
    with patch("ipat_watchdog.handlers.file_event_handler.SettingsStore.get", return_value=tmp_settings):
        return FileEventHandler(event_queue)


# ─────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────

def test_on_created_tiff(handler, event_queue, tmp_path):
    """
    Test the behavior when a TIFF file is created. Ensure that the debounce timer is triggered
    and the file is added to the event queue after the timer expires.
    """
    # Create a temporary TIFF file
    test_file = tmp_path / "fake_image.TIFF"
    test_file.touch()
    event = FileSystemEvent(str(test_file))

    # Patch Timer to simulate the debounce behavior
    with patch("ipat_watchdog.handlers.file_event_handler.Timer") as mock_timer:
        handler.on_created(event)

        # Check that the timer was set with the correct delay
        assert mock_timer.call_count == 1
        delay_arg = mock_timer.call_args[0][0]
        assert delay_arg == 1  # 1-second delay for TIFF files

        # Extract callback and execute it
        callback = mock_timer.call_args[0][1]
        callback_args = mock_timer.call_args[1]["args"]
        assert callback_args == [str(test_file)]

        # Trigger the callback and verify the event queue
        callback(*callback_args)
        assert not event_queue.empty()
        assert event_queue.get_nowait() == str(test_file)


def test_on_created_generic_file(handler, event_queue, tmp_path):
    """
    Test the behavior when a generic file (e.g., .txt) is created. Ensure that the debounce timer
    is triggered and the file is added to the event queue after the timer expires.
    """
    # Create a temporary .txt file
    test_file = tmp_path / "file.txt"
    test_file.touch()
    event = FileSystemEvent(str(test_file))

    with patch("ipat_watchdog.handlers.file_event_handler.Timer") as mock_timer:
        handler.on_created(event)

        # Check that the timer was set with the correct delay
        assert mock_timer.call_count == 1
        delay_arg = mock_timer.call_args[0][0]
        assert delay_arg == handler.settings.DEBOUNCE_TIME  # delay should be set from settings

        # Extract callback and execute it
        callback = mock_timer.call_args[0][1]
        callback_args = mock_timer.call_args[1]["args"]
        assert callback_args == [str(test_file)]

        # Trigger the callback and verify the event queue
        callback(*callback_args)
        assert not event_queue.empty()
        assert event_queue.get_nowait() == str(test_file)


def test_path_no_longer_exists(handler, event_queue, tmp_path):
    """
    Test the behavior when the file path no longer exists. Ensure that a warning is logged
    and the event queue remains empty.
    """
    # Create a temporary file and simulate its deletion
    test_file = tmp_path / "file_to_delete.txt"
    test_file.touch()
    event = FileSystemEvent(str(test_file))

    with patch("pathlib.Path.exists", return_value=False), patch(
        "ipat_watchdog.handlers.file_event_handler.Timer"
    ) as mock_timer, patch("ipat_watchdog.handlers.file_event_handler.logger.warning") as mock_warn:
        handler.on_created(event)

        # Ensure the timer was set
        assert mock_timer.call_count == 1
        delay_arg = mock_timer.call_args[0][0]
        assert delay_arg == handler.settings.DEBOUNCE_TIME

        # Extract callback and execute it
        callback = mock_timer.call_args[0][1]
        callback_args = mock_timer.call_args[1]["args"]
        callback(*callback_args)

        # Check that the event queue is empty and warning was logged
        assert event_queue.empty()
        mock_warn.assert_called_once()
        assert "Path no longer exists" in mock_warn.call_args[0][0]


def test_on_created_directory(handler, event_queue, tmp_path):
    """
    Test the behavior when a directory is created. Ensure that the debounce timer is triggered
    and the directory is added to the event queue after the timer expires.
    """
    # Create a temporary directory
    test_dir = tmp_path / "some_directory"
    test_dir.mkdir()
    event = DirCreatedEvent(str(test_dir))

    with patch("ipat_watchdog.handlers.file_event_handler.Timer") as mock_timer:
        handler.on_created(event)

        # Ensure the timer was set
        assert mock_timer.call_count == 1
        delay_arg = mock_timer.call_args[0][0]
        assert delay_arg == handler.settings.DEBOUNCE_TIME

        # Extract callback and execute it
        callback = mock_timer.call_args[0][1]
        callback_args = mock_timer.call_args[1]["args"]
        assert callback_args == [str(test_dir)]

        # Trigger the callback and verify the event queue
        callback(*callback_args)
        assert not event_queue.empty()
        assert event_queue.get_nowait() == str(test_dir)
