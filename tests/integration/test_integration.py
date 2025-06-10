# tests/integration/test_integration.py
"""
Happy-path & “sad-path” integration tests that exercise the real watchdog
observer and FileEventHandler.  Only the UI and DB-sync classes are faked.

Key implementation notes
------------------------
* PollingObserver is used for cross-platform reliability.
* Debounce for unknown extensions is 1 s in tmp_settings, **but** “.tif” is
  whitelisted ⇒ only 1 s wait before enqueue for valid images.
* For the invalid-extension test we no longer rely on `event_queue` because the
  jpg is rejected immediately and therefore never queued.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from watchdog.observers.polling import PollingObserver

from ipat_watchdog.core.app.device_watchdog_app import DeviceWatchdogApp
from ipat_watchdog.core.processing.file_process_manager import FileProcessManager
from ipat_watchdog.core.storage.filesystem_utils import (
    generate_record_id,
    init_dirs,
)
from ipat_watchdog.device_plugins.sem_tischrem_blb.file_processor import FileProcessorTischREM
from tests.helpers.fake_sync import DummySyncManager
from tests.helpers.fake_ui import HeadlessUI
from ipat_watchdog.core.ui.ui_messages import InfoMessages, WarningMessages

# ────────────────────────── fixtures ──────────────────────────────────────────
@pytest.fixture
def real_processing_app(tmp_settings):
    """
    Build DeviceWatchdogApp with:

      • PollingObserver           (real, cross-platform)
      • FileEventHandler          (real, default)
      • FileProcessManager +      (real)
        FileProcessorTischREM
    """
    init_dirs()  # create WATCH_DIR / DEST_DIR / … inside tmp dir

    ui = HeadlessUI()
    sync = DummySyncManager(ui=ui)

    app = DeviceWatchdogApp(
        ui=ui,
        sync_manager=sync,
        file_processor=FileProcessorTischREM(),
        observer_cls=PollingObserver,
        file_process_manager_cls=FileProcessManager,
    )

    app.initialize()          # starts observer thread immediately
    yield app
    app.on_closing()          # always stop observer & clean up


# ───────────────────────── “happy-path” test ─────────────────────────────────
def test_happy_path(real_processing_app, tmp_settings):
    prefix = "mus-ipat-sample"
    tif_path: Path = tmp_settings.WATCH_DIR / f"{prefix}.tif"
    tif_path.parent.mkdir(parents=True, exist_ok=True)
    tif_path.write_bytes(b"dummy image bytes")

    # Wait for observer + debounce timer to enqueue path
    deadline = time.time() + 5
    while time.time() < deadline and real_processing_app.event_queue.empty():
        time.sleep(0.1)

    assert not real_processing_app.event_queue.empty(), "Observer never enqueued the file"

    real_processing_app.process_events()

    # ─────────────── assertions ───────────────
    record_id = generate_record_id(prefix)
    record = real_processing_app.file_processing.records.get_record_by_id(record_id)
    assert record is not None, "LocalRecord was not created"
    assert record.datatype == "img"

    # original file moved into record folder
    assert not tif_path.exists()
    assert any(path.endswith(".tif") for path in record.files_uploaded)

    # UI: no errors or warnings
    assert real_processing_app.ui.errors == []
    assert real_processing_app.ui.warnings == []


# ───────────────────────── invalid extension test ────────────────────────────
def test_invalid_extension_moves_to_exception(real_processing_app, tmp_settings):
    """
    ‘.jpg’ should be rejected immediately, moved to EXCEPTIONS_DIR and the user
    must see an “Unsupported Input” **error** with the extension mentioned.
    """
    bad = tmp_settings.WATCH_DIR / "mus-ipat-sample.jpg"
    bad.write_bytes(b"nope")

    # Wait until the file is physically moved by the handler
    deadline = time.time() + 3
    while time.time() < deadline:
        if any(Path(tmp_settings.EXCEPTIONS_DIR).glob("mus-ipat-sample*.jpg")):
            break
        time.sleep(0.1)
    else:
        pytest.fail("File was never moved to exceptions folder")

    # Drain any pending UI messages
    real_processing_app.process_events()

    # Confirm moved file exists
    matches = list(Path(tmp_settings.EXCEPTIONS_DIR).glob("mus-ipat-sample*.jpg"))
    assert len(matches) == 1 and matches[0].exists()

    # Confirm user was warned (actually: shown as an *error*)
    assert any(
        title == "Unsupported Input" and "Unsupported file extension" in msg
        for title, msg in real_processing_app.ui.errors
    ), f"UI errors were: {real_processing_app.ui.errors}"


# ───────────────────────── invalid prefix → rename ───────────────────────────
def test_invalid_prefix_moves_to_rename(real_processing_app, tmp_settings):
    bad = tmp_settings.WATCH_DIR / "badprefix.tif"
    bad.write_bytes(b"dummy")

    deadline = time.time() + 5
    while time.time() < deadline and real_processing_app.event_queue.empty():
        time.sleep(0.1)

    real_processing_app.process_events()

    # Verify file was moved to rename folder
    matches = list(Path(tmp_settings.RENAME_DIR).glob("badprefix*.tif"))
    assert len(matches) == 1 and matches[0].exists()

    # Verify user was informed
    assert (
        InfoMessages.OPERATION_CANCELLED,
        InfoMessages.MOVED_TO_RENAME,
    ) in real_processing_app.ui.infos


# ─────────────────── interactive rename loop (happy) ─────────────────────────
def test_interactive_rename_loop_success(real_processing_app, tmp_settings):
    # simulate user correcting the bad prefix to a valid one
    real_processing_app.ui.rename_inputs.append(
        {"name": "mus", "institute": "ipat", "sample_ID": "sample"}
    )

    bad = tmp_settings.WATCH_DIR / "badprefix.tif"
    bad.write_bytes(b"dummy")

    # wait for enqueue
    deadline = time.time() + 5
    while time.time() < deadline and real_processing_app.event_queue.empty():
        time.sleep(0.1)

    real_processing_app.process_events()

    # now we expect a proper record for 'mus-ipat-sample'
    rid = generate_record_id("mus-ipat-sample")
    rec = real_processing_app.file_processing.records.get_record_by_id(rid)
    assert rec is not None
    # and that the file was moved into the record folder
    assert not bad.exists()
    assert any(p.endswith(".tif") for p in rec.files_uploaded)


# ───────────────────── session end flushes on “Done” ─────────────────────────
def test_session_end_flushes_on_done(real_processing_app, tmp_settings):
    # prepare for immediate 'Done' on session start
    real_processing_app.ui.auto_close_session = True

    prefix = "mus-ipat-sample"
    tif = tmp_settings.WATCH_DIR / f"{prefix}.tif"
    tif.write_bytes(b"x")

    # wait + drain
    deadline = time.time() + 5
    while time.time() < deadline and real_processing_app.event_queue.empty():
        time.sleep(0.1)

    real_processing_app.process_events()

    # after process_events:
    #  ─ then session.start → show_done → end_session → sync_records
    assert len(real_processing_app.sync_manager.synced_records) >= 1
