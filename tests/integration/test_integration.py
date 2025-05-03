# tests/test_integration_happy_real_observer.py
"""
Happy‑path integration test that uses the real watchdog Observer and the real
FileEventHandler.  We keep only HeadlessUI + DummySyncManager as fakes.

Implementation notes
--------------------
* PollingObserver is used rather than the default platform observer so the test
  runs reliably on Linux, macOS and Windows CI environments.
* DEBOUNCE_TIME in tmp_settings is 1 s for unknown extensions, **but** .tif is
  whitelisted; FileEventHandler therefore waits only 1 s before enqueuing.
* We poll the app’s `event_queue` for up to 5 s to allow the debounce timer and
  observer thread to fire.
"""

import time
from pathlib import Path

import pytest
from watchdog.observers.polling import PollingObserver

from ipat_watchdog.core.app.device_watchdog_app import DeviceWatchdogApp
from ipat_watchdog.core.storage.filesystem_utils import init_dirs, generate_record_id
from ipat_watchdog.core.processing.file_process_manager import FileProcessManager
from ipat_watchdog.plugins.sem_tischrem_blb.file_processor import FileProcessorTischREM

from tests.helpers.fake_ui import HeadlessUI
from tests.helpers.fake_sync import DummySyncManager


@pytest.fixture
def real_processing_app(tmp_settings):
    """
    Build DeviceWatchdogApp with:
      • PollingObserver  (real, cross‑platform)
      • FileEventHandler (real, default)
      • FileProcessManager + FileProcessorTischREM (real)
    """
    init_dirs()                     # create WATCH_DIR etc.

    ui = HeadlessUI()
    sync = DummySyncManager(ui=ui)

    app = DeviceWatchdogApp(
        ui=ui,
        sync_manager=sync,
        file_processor=FileProcessorTischREM(),
        observer_cls=PollingObserver,
        file_process_manager_cls=FileProcessManager,
    )

    app.initialize()                # starts the observer thread
    yield app
    app.on_closing()                # stop observer & clean up


def test_happy_path(real_processing_app, tmp_settings):
    prefix = "mus-ipat-sample"
    tif_path: Path = tmp_settings.WATCH_DIR / f"{prefix}.tif"
    tif_path.parent.mkdir(parents=True, exist_ok=True)
    tif_path.write_bytes(b"dummy image bytes")

    # Wait for the observer + debounce timer to stick the path into the queue
    deadline = time.time() + 5          # 5 s safety net
    while time.time() < deadline and real_processing_app.event_queue.empty():
        time.sleep(0.1)

    assert not real_processing_app.event_queue.empty(), "Observer never enqueued the file"

    # Process the event
    real_processing_app.process_events()

    # ----------------------------------------------------------
    # Assertions
    # ----------------------------------------------------------
    record_id = generate_record_id(prefix)
    record = real_processing_app.file_processing.records.get_record_by_id(record_id)
    assert record is not None, "LocalRecord was not created"
    assert record.datatype == "img"

    # original file must have been moved into the record folder
    assert not tif_path.exists()
    assert any(path.endswith(".tif") for path in record.files_uploaded.keys())

    # no UI errors/warnings
    assert real_processing_app.ui.errors == []
    assert real_processing_app.ui.warnings == []

from ipat_watchdog.core.ui.ui_messages import InfoMessages, WarningMessages

def test_invalid_extension_moves_to_exception(real_processing_app, tmp_settings):
    bad = tmp_settings.WATCH_DIR / "mus-ipat-sample.jpg"
    bad.write_bytes(b"nope")

    deadline = time.time() + 5
    while time.time() < deadline and real_processing_app.event_queue.empty():
        time.sleep(0.1)

    assert not real_processing_app.event_queue.empty(), "jpg never enqueued"
    real_processing_app.process_events()

    matches = list(Path(tmp_settings.EXCEPTIONS_DIR).glob("mus-ipat-sample*.jpg"))
    assert len(matches) == 1
    assert matches[0].exists()

    assert any(
        WarningMessages.INVALID_DATA_TYPE_DETAILS in msg
        for _, msg in real_processing_app.ui.warnings
    )

    matches[0].unlink()


def test_invalid_prefix_moves_to_rename(real_processing_app, tmp_settings):
    bad = tmp_settings.WATCH_DIR / "badprefix.tif"
    bad.write_bytes(b"dummy")

    deadline = time.time() + 5
    while time.time() < deadline and real_processing_app.event_queue.empty():
        time.sleep(0.1)

    real_processing_app.process_events()

    # Verify file was moved to rename folder
    matches = list(Path(tmp_settings.RENAME_DIR).glob("badprefix*.tif"))
    assert len(matches) == 1
    assert matches[0].exists()

    # Verify user was informed
    assert (
        InfoMessages.OPERATION_CANCELLED,
        InfoMessages.MOVED_TO_RENAME
    ) in real_processing_app.ui.infos

def test_interactive_rename_loop_success(real_processing_app, tmp_settings):
    # simulate user correcting the bad prefix to a valid one
    # by feeding the HeadlessUI one set of rename_inputs:
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
    #  - then session.start → show_done → end_session → sync_records
    assert len(real_processing_app.sync_manager.synced_records) >= 1