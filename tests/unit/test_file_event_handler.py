# tests/unit/test_file_event_handler.py
from datetime import datetime, timedelta
from queue import Queue
from unittest.mock import patch, MagicMock

import pytest
from watchdog.events import DirCreatedEvent, FileSystemEvent

from ipat_watchdog.core.handlers.file_event_handler import FileEventHandler
from ipat_watchdog.core.config.settings_base import BaseSettings


# ────────────────────────────────
# Test-specific settings
# ────────────────────────────────
class TestSettings(BaseSettings):
    FAST_DEBOUNCE_SECONDS = 1
    SLOW_DEBOUNCE_SECONDS = 2
    FOLDER_STABILITY_TIMEOUT = 2

    ALLOWED_EXTENSIONS = {".txt", ".tiff"}
    EXPEDITED_EXTENSIONS = {".tiff"}
    ALLOWED_FOLDER_CONTENTS = {".odt", ".elid"}


# ────────────────────────────────
# Helpers
# ────────────────────────────────
def _advance_time(tracker, seconds: int):
    tracker.last_change = datetime.now() - timedelta(seconds=seconds)


# ────────────────────────────────
# Fixtures
# ────────────────────────────────
@pytest.fixture
def handler(event_queue, monkeypatch):
    # Replace threading.Timer with a dummy that does nothing
    class DummyTimer:
        def __init__(self, *a, **kw):
            self.args = a
            self.kw = kw
        def start(self): pass
        def cancel(self): pass

    monkeypatch.setattr(
        "ipat_watchdog.core.handlers.file_event_handler.threading.Timer",
        DummyTimer,
    )

    h = FileEventHandler(event_queue, settings=TestSettings())
    yield h

    # Ensure no dangling timers
    h.shutdown()


@pytest.fixture
def event_queue():
    return Queue()


# ────────────────────────────────
# File tests
# ────────────────────────────────
def test_on_created_expedited_file(handler, event_queue, tmp_path):
    f = tmp_path / "image.TIFF"
    f.touch()
    event = FileSystemEvent(str(f))

    with patch(
        "ipat_watchdog.core.handlers.file_event_handler.threading.Timer",
        new=MagicMock(),
    ) as mock_timer:
        handler.on_created(event)
        assert mock_timer.call_count == 1
        delay = mock_timer.call_args[0][0]
        assert delay == handler.settings.FAST_DEBOUNCE_SECONDS


def test_on_created_generic_file(handler, event_queue, tmp_path):
    f = tmp_path / "doc.txt"
    f.touch()
    event = FileSystemEvent(str(f))

    with patch(
        "ipat_watchdog.core.handlers.file_event_handler.threading.Timer",
        new=MagicMock(),
    ) as mock_timer:
        handler.on_created(event)
        assert mock_timer.call_count == 1
        delay = mock_timer.call_args[0][0]
        assert delay == handler.settings.SLOW_DEBOUNCE_SECONDS


def test_reject_invalid_file(handler, event_queue, tmp_path):
    bad = tmp_path / "virus.exe"
    bad.touch()
    event = FileSystemEvent(str(bad))

    handler.on_created(event)

    rejected = handler.get_and_clear_rejected()
    assert rejected and rejected[0][0] == str(bad)
    assert event_queue.empty()
    assert handler.get_and_clear_rejected() == []


# ────────────────────────────────
# Folder tests
# ────────────────────────────────
def test_accept_valid_folder(handler, event_queue, tmp_path):
    folder = tmp_path / "good_folder"
    folder.mkdir()

    for ext in handler.settings.ALLOWED_FOLDER_CONTENTS:
        (folder / f"file{ext.lower()}").touch()

    event = DirCreatedEvent(str(folder))
    handler.on_created(event)

    tracker = handler._folder_trackers[str(folder)]
    tracker.last_exts = {ext.lower() for ext in handler.settings.ALLOWED_FOLDER_CONTENTS}
    tracker.last_change -= timedelta(seconds=handler.settings.SLOW_DEBOUNCE_SECONDS + 1)
    tracker._poll()

    assert event_queue.get_nowait() == str(folder)
    assert handler.get_and_clear_rejected() == []


def test_reject_invalid_folder(handler, event_queue, tmp_path, monkeypatch):
    folder = tmp_path / "bad_folder"
    folder.mkdir()
    (folder / "irrelevant.tmp").touch()

    # prevent rescheduling inside tracker
    monkeypatch.setattr(
        "ipat_watchdog.core.handlers.file_event_handler.FileEventHandler._FolderTracker._schedule_next",
        lambda self: None,
    )

    handler.on_created(DirCreatedEvent(str(folder)))
    tracker = handler._folder_trackers[str(folder)]

    tracker.last_exts = {".tmp"}                       # pretend contents unchanged
    _advance_time(tracker, handler.settings.FOLDER_STABILITY_TIMEOUT + 1)
    tracker._poll()

    assert event_queue.empty()
    rejected = handler.get_and_clear_rejected()
    assert rejected and rejected[0][0] == str(folder)
