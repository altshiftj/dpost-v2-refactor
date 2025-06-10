from datetime import datetime, timedelta
from queue import Queue
from unittest.mock import patch, MagicMock
import shutil
import os
import time
from pathlib import Path

import pytest
from watchdog.events import DirCreatedEvent, FileSystemEvent

from ipat_watchdog.core.handlers.file_event_handler import FileEventHandler
from ipat_watchdog.core.config.settings_base import BaseSettings

# ───────────────────────────── Test-specific settings ──────────────────────────
class TestSettings(BaseSettings):
    FAST_DEBOUNCE_SECONDS = 1
    SLOW_DEBOUNCE_SECONDS = 2
    FOLDER_STABILITY_TIMEOUT = 2

    ALLOWED_EXTENSIONS = {".txt", ".tiff"}
    EXPEDITED_EXTENSIONS = {".tiff"}
    ALLOWED_FOLDER_CONTENTS = {".odt", ".elid"}

    EXCEPTIONS_DIR: str | os.PathLike | None = None


# ───────────────────────────────── helpers ─────────────────────────────────────
def _advance_time(tracker, seconds: int) -> None:
    tracker.last_change = datetime.now() - timedelta(seconds=seconds)

def wait_for_moved_folder(prefix: str, base_dir: Path, timeout=0.5) -> list[Path]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        moved = list(base_dir.glob(f"{prefix}*"))
        if moved:
            return moved
        time.sleep(0.05)
    return []

# ─────────────────────────────── fixtures ──────────────────────────────────────
@pytest.fixture
def handler(event_queue, monkeypatch, tmp_path):
    class DummyTimer:
        def __init__(self, *a, **kw): pass
        def start(self): pass
        def cancel(self): pass

    monkeypatch.setattr(
        "ipat_watchdog.core.handlers.file_event_handler.threading.Timer",
        DummyTimer,
    )

    TestSettings.EXCEPTIONS_DIR = tmp_path / "exceptions"
    TestSettings.EXCEPTIONS_DIR.mkdir()

    h = FileEventHandler(event_queue, settings=TestSettings())

    monkeypatch.setattr(
        "ipat_watchdog.core.storage.filesystem_utils.SettingsStore.get",
        lambda: h.settings,
    )
    yield h
    h.shutdown()


@pytest.fixture
def event_queue():
    return Queue()


# ───────────────────────────── File-related tests ─────────────────────────────
def test_on_created_expedited_file(handler, event_queue, tmp_path):
    f = tmp_path / "image.TIFF"
    f.touch()
    event = FileSystemEvent(str(f))

    with patch(
        "ipat_watchdog.core.handlers.file_event_handler.threading.Timer",
        new=MagicMock(),
    ) as mock_timer:
        handler.on_created(event)
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
        delay = mock_timer.call_args[0][0]
        assert delay == handler.settings.SLOW_DEBOUNCE_SECONDS


def test_invalid_file_moves_to_exceptions(handler, event_queue, tmp_path):
    bad = tmp_path / "virus.exe"
    bad.touch()

    handler.on_created(FileSystemEvent(str(bad)))

    assert not bad.exists()

    moved = wait_for_moved_folder("virus", Path(handler.settings.EXCEPTIONS_DIR))
    assert any(p.suffix == ".exe" and p.is_file() for p in moved)

    rejected = handler.get_and_clear_rejected()
    assert rejected and rejected[0][0] == str(bad)
    assert event_queue.empty()


def test_timer_cap_rejects_extra_file(handler, event_queue, tmp_path):
    handler._max_active_timers = 1

    first = tmp_path / "a.txt";   first.touch()
    second = tmp_path / "b.txt";  second.touch()

    handler.on_created(FileSystemEvent(str(first)))
    handler.on_created(FileSystemEvent(str(second)))

    rejected = handler.get_and_clear_rejected()
    assert len(rejected) == 1 and rejected[0][0] == str(second)
    assert str(first) in handler._timers
    assert event_queue.empty()


# ───────────────────────────── Folder-related tests ───────────────────────────
def test_accept_valid_folder(handler, event_queue, tmp_path):
    folder = tmp_path / "good_folder"; folder.mkdir()
    for ext in handler.settings.ALLOWED_FOLDER_CONTENTS:
        (folder / f"file{ext}").touch()

    handler.on_created(DirCreatedEvent(str(folder)))

    tracker = handler._folder_trackers[str(folder)]
    tracker.last_exts = {e.lower() for e in handler.settings.ALLOWED_FOLDER_CONTENTS}
    _advance_time(tracker, handler.settings.SLOW_DEBOUNCE_SECONDS + 1)
    tracker._poll()

    assert event_queue.get_nowait() == str(folder)
    assert handler.get_and_clear_rejected() == []


def test_invalid_folder_moves_to_exceptions(handler, event_queue, tmp_path, monkeypatch):
    folder = tmp_path / "bad_folder"; folder.mkdir()
    (folder / "irrelevant.tmp").touch()

    # Disable automatic re-polling
    monkeypatch.setattr(
        "ipat_watchdog.core.handlers.file_event_handler.FileEventHandler._FolderTracker._schedule_next",
        lambda self: None,
    )

    handler.on_created(DirCreatedEvent(str(folder)))
    tracker = handler._folder_trackers[str(folder)]

    # Make tracker think nothing changed since we created the .tmp file
    tracker.last_exts = {".tmp"}
    _advance_time(tracker, handler.settings.FOLDER_STABILITY_TIMEOUT + 1)
    tracker._poll()

    moved = wait_for_moved_folder("bad_folder", Path(handler.settings.EXCEPTIONS_DIR))
    assert any(p.is_dir() for p in moved)

    rejected = handler.get_and_clear_rejected()
    assert rejected and rejected[0][0] == str(folder)
    assert event_queue.empty()



def test_tracker_cap_rejects_extra_folder(handler, tmp_path):
    handler._max_active_trackers = 1

    folder1 = tmp_path / "f1"; folder1.mkdir()
    folder2 = tmp_path / "f2"; folder2.mkdir()

    handler.on_created(DirCreatedEvent(str(folder1)))
    handler.on_created(DirCreatedEvent(str(folder2)))

    assert str(folder1) in handler._folder_trackers
    rejected = handler.get_and_clear_rejected()
    assert len(rejected) == 1 and rejected[0][0] == str(folder2)


# ───────────────────────────── Shutdown safety ────────────────────────────────
def test_shutdown_cleans_all(handler, tmp_path):
    folder = tmp_path / "folder"; folder.mkdir()
    handler.on_created(DirCreatedEvent(str(folder)))
    file_ = tmp_path / "doc.txt"; file_.touch()
    handler.on_created(FileSystemEvent(str(file_)))

    assert handler._folder_trackers or handler._timers
    handler.shutdown()
    assert handler._folder_trackers == {}
    assert handler._timers == {}
