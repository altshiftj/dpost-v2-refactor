import pytest
from unittest.mock import patch, MagicMock
from watchdog.events import FileSystemEvent, DirCreatedEvent
from queue import Queue
from pathlib import Path

from core.handlers.file_event_handler import FileEventHandler


@pytest.fixture
def event_queue():
    return Queue()


@pytest.fixture
def mock_settings():
    mock = MagicMock()
    mock.ALLOWED_EXTENSIONS = {".tif", ".tiff"}
    mock.DEBOUNCE_TIME = 2
    return mock


@pytest.fixture
def handler(event_queue, mock_settings):
    with patch("core.handlers.file_event_handler.SettingsStore.get", return_value=mock_settings):
        return FileEventHandler(event_queue)


def test_on_created_tiff(handler, event_queue):
    with patch("pathlib.Path.exists", return_value=True), patch(
        "core.handlers.file_event_handler.Timer"
    ) as mock_timer:

        fake_path = "/some/fake_image.TIFF"
        event = FileSystemEvent(fake_path)

        handler.on_created(event)

        assert mock_timer.call_count == 1
        args, kwargs = mock_timer.call_args
        assert args[0] == 1  # 1-second delay for allowed extensions
        callback = args[1]
        callback_args = kwargs.get("args", [])
        assert callback_args == [fake_path]

        callback(*callback_args)
        assert not event_queue.empty()
        assert event_queue.get_nowait() == fake_path


def test_on_created_generic_file(handler, event_queue):
    with patch("pathlib.Path.exists", return_value=True), patch(
        "core.handlers.file_event_handler.Timer"
    ) as mock_timer:

        fake_path = "/some/file.txt"
        event = FileSystemEvent(fake_path)

        handler.on_created(event)

        assert mock_timer.call_count == 1
        args, kwargs = mock_timer.call_args
        assert args[0] == handler.settings.DEBOUNCE_TIME
        callback = args[1]
        callback_args = kwargs.get("args", [])
        assert callback_args == [fake_path]

        callback(*callback_args)
        assert not event_queue.empty()
        assert event_queue.get_nowait() == fake_path


def test_path_no_longer_exists(handler, event_queue):
    with patch("pathlib.Path.exists", return_value=False), patch(
        "core.handlers.file_event_handler.Timer"
    ) as mock_timer, patch("core.handlers.file_event_handler.logger.warning") as mock_warn:

        fake_path = "/nonexistent/file.doc"
        event = FileSystemEvent(fake_path)

        handler.on_created(event)
        assert mock_timer.call_count == 1

        args, kwargs = mock_timer.call_args
        callback = args[1]
        callback_args = kwargs.get("args", [])
        callback(*callback_args)

        assert event_queue.empty()
        mock_warn.assert_called_once()
        assert "Path no longer exists" in mock_warn.call_args[0][0]


def test_on_created_directory(handler, event_queue):
    with patch("pathlib.Path.exists", return_value=True), patch(
        "pathlib.Path.is_dir", return_value=True
    ), patch("core.handlers.file_event_handler.Timer") as mock_timer:

        fake_dir = "/some/directory"
        event = DirCreatedEvent(fake_dir)

        handler.on_created(event)
        assert mock_timer.call_count == 1

        args, kwargs = mock_timer.call_args
        callback = args[1]
        callback_args = kwargs.get("args", [])
        callback(*callback_args)

        assert not event_queue.empty()
        assert event_queue.get_nowait() == fake_dir
