"""Integration tests for the DeviceWatchdogApp with the real processing stack."""
from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from dpost.application.interactions.messages import InfoMessages
from dpost.application.processing.file_process_manager import FileProcessManager
from dpost.domain.processing.models import ProcessingStatus
from dpost.application.runtime.device_watchdog_app import DeviceWatchdogApp
from dpost.infrastructure.storage.filesystem_utils import init_dirs
from tests.helpers.fake_observer import FakeObserver
from tests.helpers.fake_sync import DummySyncManager
from tests.helpers.fake_ui import HeadlessUI
from tests.helpers.task_runner import advance_scheduled_time, drain_scheduled_tasks


def _assert_processed_artifact(tmp_settings, institute: str, user: str, sample: str, extension: str = ".tif") -> Path:
    destination = tmp_settings.DEST_DIR / institute.upper() / user.upper() / f"TEST-{sample}"
    assert destination.exists(), f"Expected destination folder {destination!s} to exist"
    matches = [f for f in destination.iterdir() if f.suffix == extension]
    assert len(matches) == 1, f"Expected exactly one {extension} artefact in {destination}, found {matches}"
    return matches[0]


@pytest.fixture
def real_processing_app(config_service, tmp_settings, monkeypatch):
    """Build a DeviceWatchdogApp wired to real processors and a stub observer."""
    ui = HeadlessUI(use_virtual_time=True)
    sync = DummySyncManager(ui)
    init_dirs([str(path) for path in config_service.current.directory_list])

    observer_stub = FakeObserver()
    app = DeviceWatchdogApp(
        ui=cast(Any, ui),  # HeadlessUI implements UserInteractionPort, which is compatible with UserInterface
        sync_manager=sync,
        config_service=config_service,
        file_process_manager_cls=FileProcessManager,
        observer_factory=lambda: observer_stub,
    )
    # Expose sync manager for assertions without mutating DeviceWatchdogApp internals
    setattr(ui, "sync_manager", sync)

    app.initialize()
    try:
        yield app
    finally:
        app.on_closing()


# ---------------------------------------------------------------------------
# "Happy path" scenarios
# ---------------------------------------------------------------------------


def test_happy_path(real_processing_app, tmp_settings):
    prefix = "mus-ipat-sample"
    tif_path = tmp_settings.WATCH_DIR / f"{prefix}.tif"
    tif_path.parent.mkdir(parents=True, exist_ok=True)
    tif_path.write_bytes(b"dummy image bytes")

    real_processing_app.file_processing.process_item(str(tif_path))
    drain_scheduled_tasks(real_processing_app.ui)

    artefact = _assert_processed_artifact(tmp_settings, "ipat", "mus", "sample")
    assert artefact.name.startswith("TEST-sample-")
    assert not tif_path.exists(), "Original file should be moved, not copied"


# ---------------------------------------------------------------------------
# Event queue processing
# ---------------------------------------------------------------------------


def test_event_queue_processes_pending_items(real_processing_app, tmp_settings):
    prefix = "mus-ipat-queued"
    queued = tmp_settings.WATCH_DIR / f"{prefix}.tif"
    queued.write_bytes(b"queued data")

    real_processing_app.event_queue.put(str(queued))
    drain_scheduled_tasks(real_processing_app.ui)

    _assert_processed_artifact(tmp_settings, "ipat", "mus", "queued")
    assert not queued.exists()


def test_retry_schedule_honors_virtual_delay(real_processing_app, tmp_settings):
    """Integration app retries should enqueue only after the scheduled delay."""
    target = tmp_settings.WATCH_DIR / "mus-ipat-delay.tif"
    target.write_bytes(b"retry me")

    real_processing_app._cancel_event_poll()
    real_processing_app._schedule_retry(str(target), 2.0)

    assert real_processing_app.event_queue.empty()

    advance_scheduled_time(real_processing_app.ui, 1500)
    assert real_processing_app.event_queue.empty()

    advance_scheduled_time(real_processing_app.ui, 500)
    assert real_processing_app.event_queue.get_nowait() == str(target)


# ---------------------------------------------------------------------------
# Invalid routing scenarios
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename, expected_dir, expected_message",
    [
        pytest.param(
            "mus-ipat-sample.jpg",
            "exceptions",
            None,
            id="invalid-extension",
        ),
        pytest.param(
            "badprefix.tif",
            "rename",
            (InfoMessages.OPERATION_CANCELLED, InfoMessages.MOVED_TO_RENAME),
            id="invalid-prefix",
        ),
    ],
)
def test_invalid_inputs_route_to_expected_bucket(real_processing_app, tmp_settings, filename, expected_dir, expected_message):
    target = tmp_settings.WATCH_DIR / filename
    target.write_bytes(b"invalid payload")

    result = real_processing_app.file_processing.process_item(str(target))
    drain_scheduled_tasks(real_processing_app.ui)

    assert result.status is ProcessingStatus.REJECTED

    bucket = tmp_settings.EXCEPTIONS_DIR if expected_dir == "exceptions" else tmp_settings.RENAME_DIR
    stem, suffix = Path(filename).stem, Path(filename).suffix
    matches = list(bucket.glob(f"{stem}*{suffix}"))
    assert len(matches) == 1, f"Expected exactly one entry in {bucket}, found {matches}"
    assert matches[0].exists()

    if expected_message is not None:
        assert real_processing_app.ui.calls["show_info"][-1] == expected_message


# ---------------------------------------------------------------------------
# Interactive rename happy path
# ---------------------------------------------------------------------------


def test_interactive_rename_loop_success(real_processing_app, tmp_settings):
    real_processing_app.ui.rename_inputs.append({"name": "mus", "institute": "ipat", "sample_ID": "sample"})

    bad = tmp_settings.WATCH_DIR / "badprefix.tif"
    bad.write_bytes(b"dummy")

    real_processing_app.file_processing.process_item(str(bad))
    drain_scheduled_tasks(real_processing_app.ui)

    artefact = _assert_processed_artifact(tmp_settings, "ipat", "mus", "sample")
    assert artefact.name.endswith(".tif")
    assert not bad.exists()


# ---------------------------------------------------------------------------
# Session end triggers record sync
# ---------------------------------------------------------------------------


def test_session_end_flushes_on_done(real_processing_app, tmp_settings):
    real_processing_app.ui.auto_close_session = True

    prefix = "mus-ipat-session"
    tif = tmp_settings.WATCH_DIR / f"{prefix}.tif"
    tif.write_bytes(b"x")

    real_processing_app.file_processing.process_item(str(tif))
    drain_scheduled_tasks(real_processing_app.ui)

    assert real_processing_app.file_processing.records.all_records_uploaded()
    sync_mgr = getattr(real_processing_app.ui, "sync_manager", None)
    assert sync_mgr is not None and sync_mgr.synced_records, "Expected sync manager to be invoked"


# ---------------------------------------------------------------------------
# Rapid arrivals
# ---------------------------------------------------------------------------


def test_rapid_file_arrival_same_record(real_processing_app, tmp_settings):
    base_name = "abc-xyz-testsample"
    num_files = 5

    for i in range(num_files):
        file_path = tmp_settings.WATCH_DIR / f"{base_name}{i}.tif"
        file_path.write_bytes(f"test data {i}".encode())
        real_processing_app.file_processing.process_item(str(file_path))
        drain_scheduled_tasks(real_processing_app.ui)

    for i in range(num_files):
        dest = tmp_settings.DEST_DIR / "XYZ" / "ABC" / f"TEST-testsample{i}"
        assert dest.exists(), f"Expected record directory {dest} not found"
        expected_file = dest / f"TEST-testsample{i}-01.tif"
        assert expected_file.exists(), f"Expected file {expected_file} not found"

    all_tif_files = list(tmp_settings.DEST_DIR.rglob("*.tif"))
    assert len(all_tif_files) == num_files, f"Expected {num_files} files, found {len(all_tif_files)}"


# ---------------------------------------------------------------------------
# Multiple files same record (serial processing)
# ---------------------------------------------------------------------------


def test_multiple_files_same_record(real_processing_app, tmp_settings):
    base_name = "usr-ipat-threadsafe"
    num_files = 3

    for i in range(num_files):
        file_path = tmp_settings.WATCH_DIR / f"{base_name}{i}.tif"
        file_path.write_bytes(f"multi-file test {i}".encode())
        real_processing_app.file_processing.process_item(str(file_path))
        drain_scheduled_tasks(real_processing_app.ui)

    for i in range(num_files):
        dest = tmp_settings.DEST_DIR / "IPAT" / "USR" / f"TEST-threadsafe{i}"
        assert dest.exists(), f"Expected directory {dest} not created"
        expected_file = dest / f"TEST-threadsafe{i}-01.tif"
        assert expected_file.exists(), f"Expected file {expected_file} not found"

    all_tif_files = list(tmp_settings.DEST_DIR.rglob("*.tif"))
    assert len(all_tif_files) == num_files, f"Expected {num_files} files, found {len(all_tif_files)}"
