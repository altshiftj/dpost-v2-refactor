
# tests/test_file_event_handler.py
from pathlib import Path
from queue import Queue
from unittest.mock import patch
import os
import time
import datetime as dt

import pytest
from watchdog.events import DirCreatedEvent, FileSystemEvent

from ipat_watchdog.core.handlers.file_event_handler import FileEventHandler

PATH_TRACKER_SCHEDULE = (
    "ipat_watchdog.core.handlers.file_event_handler.FileEventHandler._PathTracker._schedule"
)

# ─────────────────────────────── helpers ─────────────────────────────────────
def wait_for_moved(prefix: str, base_dir: Path, timeout: float = 0.5) -> list[Path]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        moved = list(base_dir.glob(f"{prefix}*"))
        if moved:
            return moved
        time.sleep(0.05)
    return []


# ─────────────────────────────── fixtures ────────────────────────────────────
@pytest.fixture
def event_queue():
    return Queue()


@pytest.fixture
def handler(event_queue, monkeypatch, tmp_settings):
    """
    •   Replace `threading.Timer` so the test thread never sleeps.
    •   Redirect SettingsStore.get() so everything downstream picks up our
        *in-memory* settings instance.
    •   Ensure we have an EXCEPTIONS_DIR that we can inspect.
    """
    class DummyTimer:
        def __init__(self, *a, **kw): pass
        def start(self): pass
        def cancel(self): pass

    monkeypatch.setattr(
        "ipat_watchdog.core.handlers.file_event_handler.threading.Timer",
        DummyTimer,
    )

    tmp_settings.EXCEPTIONS_DIR.mkdir(parents=True, exist_ok=True)

    h = FileEventHandler(event_queue, settings=tmp_settings)

    monkeypatch.setattr(
        "ipat_watchdog.core.storage.filesystem_utils.SettingsStore.get",
        lambda: h.settings,
    )

    yield h
    h.shutdown()


# ───────────────────────────── File-related tests ────────────────────────────
def test_accept_stable_file(handler, event_queue, tmp_path, monkeypatch):
    f = tmp_path / "sample.txt"
    f.write_text("hello")

    monkeypatch.setattr(PATH_TRACKER_SCHEDULE, lambda self: None)

    handler.on_created(FileSystemEvent(str(f)))
    tracker = handler._trackers[str(f)]
    tracker._check_stability()
    tracker._check_stability()
    tracker._check_stability()

    assert event_queue.get_nowait() == str(f)
    assert handler.get_and_clear_rejected() == []


def test_file_with_any_extension_gets_tracked(handler, event_queue, tmp_path, monkeypatch):
    """Test that files with any extension now get tracked instead of immediately rejected."""
    exe_file = tmp_path / "malware.exe"
    exe_file.touch()

    monkeypatch.setattr(PATH_TRACKER_SCHEDULE, lambda self: None)

    handler.on_created(FileSystemEvent(str(exe_file)))
    
    # File should be tracked (not immediately rejected)
    assert str(exe_file) in handler._trackers
    assert exe_file.exists()  # File should still exist
    assert handler.get_and_clear_rejected() == []  # No immediate rejection


def test_tracker_cap_rejects_extra_path(handler, event_queue, tmp_path):
    handler._max_active_trackers = 1

    a = tmp_path / "a.txt"; a.touch()
    b = tmp_path / "b.txt"; b.touch()

    handler.on_created(FileSystemEvent(str(a)))
    handler.on_created(FileSystemEvent(str(b)))

    rejected = handler.get_and_clear_rejected()
    assert len(rejected) == 1 and rejected[0][0] == str(b)
    assert str(a) in handler._trackers
    assert event_queue.empty()


# ───────────────────────────── Folder-related tests ──────────────────────────
def test_accept_valid_folder(handler, event_queue, tmp_path, monkeypatch):
    folder = tmp_path / "good"; folder.mkdir()
    for ext in handler.settings.ALLOWED_FOLDER_CONTENTS:
        (folder / f"f{ext}").touch()

    monkeypatch.setattr(PATH_TRACKER_SCHEDULE, lambda self: None)

    handler.on_created(DirCreatedEvent(str(folder)))
    tracker = handler._trackers[str(folder)]
    tracker._check_stability()
    

    assert event_queue.get_nowait() == str(folder)
    assert handler.get_and_clear_rejected() == []


def test_stable_but_invalid_folder_rejected(handler, tmp_path, monkeypatch):
    folder = tmp_path / "bad"; folder.mkdir()
    (folder / "ok.odt").touch()

    monkeypatch.setattr(PATH_TRACKER_SCHEDULE, lambda self: None)

    handler.on_created(DirCreatedEvent(str(folder)))
    tracker = handler._trackers[str(folder)]

    for _ in range(handler.settings.STABLE_CYCLES):
        tracker._check_stability()

    moved = wait_for_moved("bad", Path(handler.settings.EXCEPTIONS_DIR))
    assert any(p.is_dir() and p.name.startswith("bad") for p in moved)

    rejected = handler.get_and_clear_rejected()
    assert rejected and rejected[0][0] == str(folder)


def test_folder_timeout_moves_to_exceptions(handler, tmp_path, monkeypatch):
    folder = tmp_path / "timeout"; folder.mkdir()
    (folder / "growing.tmp").touch()

    monkeypatch.setattr(PATH_TRACKER_SCHEDULE, lambda self: None)

    handler.on_created(DirCreatedEvent(str(folder)))
    tracker = handler._trackers[str(folder)]
    tracker._start -= dt.timedelta(seconds=handler.settings.MAX_WAIT_SECONDS + 1)

    tracker._check_stability()

    moved = wait_for_moved("timeout", Path(handler.settings.EXCEPTIONS_DIR))
    assert any(p.is_dir() for p in moved)
    assert handler.get_and_clear_rejected()[0][0] == str(folder)


def test_folder_waits_for_sentinel(handler, tmp_path, monkeypatch, tmp_settings):
    tmp_settings.SENTINEL_NAME = "_DONE"

    folder = tmp_path / "job"; folder.mkdir()
    for ext in handler.settings.ALLOWED_FOLDER_CONTENTS:
        (folder / f"content{ext}").touch()

    monkeypatch.setattr(PATH_TRACKER_SCHEDULE, lambda self: None)

    handler.on_created(DirCreatedEvent(str(folder)))
    tr = handler._trackers[str(folder)]

    for _ in range(handler.settings.STABLE_CYCLES):
        tr._check_stability()

    assert handler.event_queue.empty()

    (folder / "_DONE").touch()
    tr._check_stability()
    assert tr._stable_count == 0

    tr._check_stability()
    assert tr._stable_count == 1
    assert handler.event_queue.get_nowait() == str(folder)


def test_temp_folder_ignored(handler, tmp_path):
    temp = tmp_path / "upload.A1B2C3"
    temp.mkdir()
    handler.on_created(DirCreatedEvent(str(temp)))
    assert str(temp) not in handler._trackers
    assert handler.get_and_clear_rejected() == []
    assert handler.event_queue.empty()


def test_file_change_resets_stability(handler, tmp_path, monkeypatch):
    f = tmp_path / "video.txt"
    f.write_bytes(b"0"*10)

    monkeypatch.setattr(PATH_TRACKER_SCHEDULE, lambda self: None)
    handler.on_created(FileSystemEvent(str(f)))
    tr = handler._trackers[str(f)]

    tr._check_stability()
    f.write_bytes(b"1"*20)
    tr._check_stability()
    assert tr._stable_count == 0


def test_disappearing_file_is_ignored(handler, tmp_path, monkeypatch):
    p = tmp_path / "ghost.txt"
    p.write_text("x")

    monkeypatch.setattr(PATH_TRACKER_SCHEDULE, lambda self: None)
    handler.on_created(FileSystemEvent(str(p)))
    tr = handler._trackers[str(p)]

    p.unlink()
    tr._check_stability()

    assert handler.get_and_clear_rejected() == []


def test_duplicate_on_created_restarts_tracker(handler, tmp_path, monkeypatch):
    path = tmp_path / "dup.txt"; path.touch()

    monkeypatch.setattr(PATH_TRACKER_SCHEDULE, lambda self: None)

    handler.on_created(FileSystemEvent(str(path)))
    first_tracker = handler._trackers[str(path)]
    first_tracker._stable_count = 5

    handler.on_created(FileSystemEvent(str(path)))
    second_tracker = handler._trackers[str(path)]

    assert second_tracker._stable_count == 0
    assert second_tracker is not first_tracker


def test_shutdown_cleans_all(handler, tmp_path):
    folder = tmp_path / "fold"; folder.mkdir()
    file_ = tmp_path / "doc.txt"; file_.touch()

    handler.on_created(DirCreatedEvent(str(folder)))
    handler.on_created(FileSystemEvent(str(file_)))

    assert handler._trackers
    handler.shutdown()
    assert handler._trackers == {}
