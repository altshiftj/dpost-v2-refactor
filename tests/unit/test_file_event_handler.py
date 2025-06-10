# tests/test_file_event_handler.py
from pathlib import Path
from queue import Queue
from unittest.mock import patch, MagicMock
import os
import time

import pytest
from watchdog.events import DirCreatedEvent, FileSystemEvent

# --------------------------------------------------------------------------- #
#  SUT
# --------------------------------------------------------------------------- #
from ipat_watchdog.core.handlers.file_event_handler import FileEventHandler
from ipat_watchdog.core.config.settings_base import BaseSettings


# ───────────────────────────── Test-specific settings ────────────────────────
class TestSettings(BaseSettings):
    """
    Minimal settings for unit tests.
    We keep the names the new handler actually looks at.
    """
    # polling / timeout
    POLL_SECONDS = 0.1        # keep it tiny so we don’t wait in real time
    MAX_WAIT_SECONDS = 2.0

    # validation rules
    ALLOWED_EXTENSIONS = {".txt", ".tiff"}
    ALLOWED_FOLDER_CONTENTS = {".odt", ".elid"}

    # where move_to_exception_folder() will place rejected artefacts
    EXCEPTIONS_DIR: str | os.PathLike | None = None


# ─────────────────────────────── helpers ─────────────────────────────────────
def wait_for_moved(prefix: str, base_dir: Path, timeout: float = 0.5) -> list[Path]:
    """
    Utility: wait a short time for the handler to move a rejected path
    into the exceptions directory and return the moved items.
    """
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
def handler(event_queue, monkeypatch, tmp_path):
    """
    •   Replace `threading.Timer` so the test thread never sleeps.
    •   Redirect SettingsStore.get() so everything downstream picks up our
        *in-memory* TestSettings instance.
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

    TestSettings.EXCEPTIONS_DIR = tmp_path / "exceptions"
    TestSettings.EXCEPTIONS_DIR.mkdir()

    h = FileEventHandler(event_queue, settings=TestSettings())

    monkeypatch.setattr(
        "ipat_watchdog.core.storage.filesystem_utils.SettingsStore.get",
        lambda: h.settings,
    )
    yield h
    h.shutdown()


# ───────────────────────────── File-related tests ────────────────────────────
def test_accept_stable_file(handler, event_queue, tmp_path, monkeypatch):
    """
    A supported single file should be queued after the first stability check.
    """
    f = tmp_path / "sample.txt"
    f.write_text("hello")

    # disable the automatic re-schedule so we stay synchronous
    monkeypatch.setattr(
        "ipat_watchdog.core.handlers.file_event_handler."
        "FileEventHandler._PathTracker._schedule",
        lambda self: None,
    )

    handler.on_created(FileSystemEvent(str(f)))

    tracker = handler._trackers[str(f)]
    tracker._check_stability()              # pretend the timer fired

    assert event_queue.get_nowait() == str(f)
    assert handler.get_and_clear_rejected() == []


def test_invalid_file_moves_to_exceptions(handler, event_queue, tmp_path):
    """
    An unsupported extension is rejected immediately and moved.
    """
    bad = tmp_path / "malware.exe"
    bad.touch()

    handler.on_created(FileSystemEvent(str(bad)))

    assert not bad.exists()                 # source vanished ⇒ moved
    moved = wait_for_moved("malware", Path(handler.settings.EXCEPTIONS_DIR))
    assert any(p.suffix == ".exe" for p in moved)

    rejected = handler.get_and_clear_rejected()
    assert rejected and rejected[0][0] == str(bad)
    assert event_queue.empty()


def test_tracker_cap_rejects_extra_path(handler, event_queue, tmp_path):
    """
    With the per-handler tracker limit set to 1, the 2nd path is rejected.
    """
    handler._max_active_trackers = 1

    a = tmp_path / "a.txt";  a.touch()
    b = tmp_path / "b.txt";  b.touch()

    handler.on_created(FileSystemEvent(str(a)))
    handler.on_created(FileSystemEvent(str(b)))

    rejected = handler.get_and_clear_rejected()
    assert len(rejected) == 1 and rejected[0][0] == str(b)
    assert str(a) in handler._trackers
    assert event_queue.empty()


# ───────────────────────────── Folder-related tests ──────────────────────────
def test_accept_valid_folder(handler, event_queue, tmp_path, monkeypatch):
    """
    A folder that already contains all required files is accepted on first check.
    """
    folder = tmp_path / "good"; folder.mkdir()
    for ext in handler.settings.ALLOWED_FOLDER_CONTENTS:
        (folder / f"f{ext}").touch()

    monkeypatch.setattr(
        "ipat_watchdog.core.handlers.file_event_handler."
        "FileEventHandler._PathTracker._schedule",
        lambda self: None,
    )

    handler.on_created(DirCreatedEvent(str(folder)))
    tracker = handler._trackers[str(folder)]
    tracker._check_stability()

    assert event_queue.get_nowait() == str(folder)
    assert handler.get_and_clear_rejected() == []


def test_invalid_folder_moves_to_exceptions(handler, event_queue, tmp_path, monkeypatch):
    """
    A folder missing required content is rejected as soon as it is stable.
    """
    folder = tmp_path / "bad"; folder.mkdir()
    (folder / "junk.tmp").touch()

    monkeypatch.setattr(
        "ipat_watchdog.core.handlers.file_event_handler."
        "FileEventHandler._PathTracker._schedule",
        lambda self: None,
    )

    handler.on_created(DirCreatedEvent(str(folder)))
    tracker = handler._trackers[str(folder)]
    tracker._check_stability()

    moved = wait_for_moved("bad", Path(handler.settings.EXCEPTIONS_DIR))
    assert any(p.is_dir() for p in moved)

    rejected = handler.get_and_clear_rejected()
    assert rejected and rejected[0][0] == str(folder)
    assert event_queue.empty()


# ───────────────────────────── Shutdown safety ───────────────────────────────
def test_shutdown_cleans_all(handler, tmp_path):
    """
    All active trackers should be stopped & removed on shutdown.
    """
    folder = tmp_path / "fold"; folder.mkdir()
    file_ = tmp_path / "doc.txt"; file_.touch()

    handler.on_created(DirCreatedEvent(str(folder)))
    handler.on_created(FileSystemEvent(str(file_)))

    assert handler._trackers                 # something is being tracked
    handler.shutdown()
    assert handler._trackers == {}
