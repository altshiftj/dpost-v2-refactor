import pytest
from unittest.mock import patch
from watchdog.events import FileSystemEvent, DirCreatedEvent
from queue import Queue

from src.handlers.file_event_handler import FileEventHandler

@pytest.fixture
def event_queue():
    return Queue()

@pytest.fixture
def handler(event_queue):
    return FileEventHandler(event_queue)


def test_on_created_tiff(handler, event_queue):
    with patch("os.path.exists", return_value=True), \
         patch("threading.Timer") as mock_timer:

        fake_path = "/some/fake_image.TIFF"
        event = FileSystemEvent(fake_path)

        handler.on_created(event)

        assert mock_timer.call_count == 1
        args, kwargs = mock_timer.call_args
        assert args[0] == 1
        callback = args[1]
        callback_args = kwargs.get("args", [])
        assert callback_args == [fake_path]

        callback(*callback_args)
        assert not event_queue.empty()
        queued_path = event_queue.get_nowait()
        assert queued_path == fake_path


def test_on_created_generic_file(handler, event_queue):
    with patch("os.path.exists", return_value=True), \
         patch("threading.Timer") as mock_timer:

        fake_path = "/some/file.txt"
        event = FileSystemEvent(fake_path)

        handler.on_created(event)

        assert mock_timer.call_count == 1
        args, kwargs = mock_timer.call_args
        assert args[0] == handler.debounce_time
        callback = args[1]
        callback_args = kwargs.get("args", [])
        assert callback_args == [fake_path]

        callback(*callback_args)
        assert not event_queue.empty()
        assert event_queue.get_nowait() == fake_path


def test_path_no_longer_exists(handler, event_queue):
    with patch("os.path.exists", return_value=False), \
         patch("threading.Timer") as mock_timer, \
         patch("logging.Logger.warning") as mock_warn:

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
    with patch("os.path.exists", return_value=True), \
         patch("threading.Timer") as mock_timer:

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
