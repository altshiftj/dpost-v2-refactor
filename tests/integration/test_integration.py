from __future__ import annotations

import time
import os
from pathlib import Path

import pytest
from watchdog.observers.polling import PollingObserver

from ipat_watchdog.core.app.device_watchdog_app import DeviceWatchdogApp
from ipat_watchdog.core.processing.file_process_manager import FileProcessManager
from ipat_watchdog.core.storage.filesystem_utils import (
    generate_record_id,
    init_dirs,
)
from ipat_watchdog.device_plugins.sem_phenomxl2.file_processor import FileProcessorSEMPhenomXL2
from tests.helpers.fake_sync import DummySyncManager
from tests.helpers.fake_ui import HeadlessUI
from ipat_watchdog.core.ui.ui_messages import InfoMessages


# ────────────────────────── fixtures ──────────────────────────────────────────
@pytest.fixture
def real_processing_app(tmp_settings):
    """
    Build DeviceWatchdogApp with:

      • PollingObserver           (real, cross-platform)
      • FileEventHandler          (real, default)
      • FileProcessManager        (real, with test device support)
    """

    ui = HeadlessUI()
    sync = DummySyncManager(ui=ui)

    # Set up SettingsManager with test device plugin for proper test isolation
    from ipat_watchdog.core.config.settings_store import SettingsStore, SettingsManager
    from ipat_watchdog.device_plugins.test_device.plugin import TestDevicePlugin
    from ipat_watchdog.pc_plugins.default_pc_blb.plugin import DefaultPCPlugin

    # Load the test device plugin
    test_device = TestDevicePlugin()
    test_device_settings = test_device.get_settings()
    
    # Override paths to use the temporary directory from tmp_settings
    test_device_settings.APP_DIR = tmp_settings.APP_DIR
    test_device_settings.WATCH_DIR = tmp_settings.WATCH_DIR
    test_device_settings.DEST_DIR = tmp_settings.DEST_DIR
    test_device_settings.RENAME_DIR = tmp_settings.RENAME_DIR
    test_device_settings.EXCEPTIONS_DIR = tmp_settings.EXCEPTIONS_DIR
    test_device_settings.DAILY_RECORDS_JSON = tmp_settings.DAILY_RECORDS_JSON
    test_device_settings.LOG_FILE = tmp_settings.LOG_FILE
    
    # Override for faster testing
    test_device_settings.POLL_SECONDS = tmp_settings.POLL_SECONDS
    test_device_settings.STABLE_CYCLES = tmp_settings.STABLE_CYCLES
    test_device_settings.MAX_WAIT_SECONDS = tmp_settings.MAX_WAIT_SECONDS
    test_device_settings.SESSION_TIMEOUT = tmp_settings.SESSION_TIMEOUT
    test_device_settings.DEBOUNCE_TIME = tmp_settings.DEBOUNCE_TIME
    
    # Load PC plugin and override its paths with test paths
    pc_plugin = DefaultPCPlugin()
    pc_settings = pc_plugin.get_settings()
    
    # Override PC settings paths to use temporary directory
    pc_settings.APP_DIR = tmp_settings.APP_DIR
    pc_settings.WATCH_DIR = tmp_settings.WATCH_DIR
    pc_settings.DEST_DIR = tmp_settings.DEST_DIR
    pc_settings.RENAME_DIR = tmp_settings.RENAME_DIR
    pc_settings.EXCEPTIONS_DIR = tmp_settings.EXCEPTIONS_DIR
    pc_settings.DAILY_RECORDS_JSON = tmp_settings.DAILY_RECORDS_JSON
    
    # Override PC settings for faster testing
    pc_settings.POLL_SECONDS = tmp_settings.POLL_SECONDS
    pc_settings.STABLE_CYCLES = tmp_settings.STABLE_CYCLES
    pc_settings.MAX_WAIT_SECONDS = tmp_settings.MAX_WAIT_SECONDS
    
    # Set up settings manager with available devices and current device context
    settings_manager = SettingsManager([test_device_settings], pc_settings)
    settings_manager.set_current_device("test_device")
    SettingsStore.set_manager(settings_manager)

    # Now create directories using the proper settings
    init_dirs()  # create WATCH_DIR / DEST_DIR / … inside tmp dir

    app = DeviceWatchdogApp(
        ui=ui,
        sync_manager=sync,
        settings_manager=settings_manager,
        observer_cls=PollingObserver,
        file_process_manager_cls=FileProcessManager,
    )

    app.initialize()          # starts observer thread immediately
    yield app
    app.on_closing()          # always stop observer & clean up


# ───────────────────────── “happy-path” test ─────────────────────────────────
def test_happy_path(real_processing_app, tmp_settings):
    prefix = "mus-ipat-sample"
    tif_path = tmp_settings.WATCH_DIR / f"{prefix}.tif"
    tif_path.parent.mkdir(parents=True, exist_ok=True)

    tif_path.write_bytes(b"dummy image bytes")

    # Process the file directly instead of waiting for file watcher
    real_processing_app.file_processing.process_item(str(tif_path))

    # Check that the file was processed correctly by looking for the moved file
    # Test device moves files to Data/INSTITUTE/USER/DEVICE_ABBR-SAMPLE/ structure
    expected_dir = tmp_settings.DEST_DIR / "IPAT" / "MUS" / "TEST-sample"
    assert expected_dir.exists(), f"Expected directory {expected_dir} does not exist"
    
    files_in_dir = list(expected_dir.iterdir())
    # Look for a file that starts with "TEST-sample-"
    tif_files = [f for f in files_in_dir if f.suffix == '.tif' and f.name.startswith('TEST-sample-')]
    assert len(tif_files) == 1, f"Expected exactly 1 processed TIF file, found {len(tif_files)}: {tif_files}"
    assert tif_files[0].exists(), f"Processed file should exist: {tif_files[0]}"
    
    # Verify the original file was moved (not copied)
    assert not tif_path.exists(), f"Original file should be moved, not copied: {tif_path}"


# ───────────────────────── invalid extension test ────────────────────────────
def test_invalid_extension_moves_to_exception(real_processing_app, tmp_settings):
    bad = tmp_settings.WATCH_DIR / "mus-ipat-sample.jpg"
    bad.write_bytes(b"nope")

    # Process the file directly
    real_processing_app.file_processing.process_item(str(bad))

    # Check if file was moved to exceptions
    exception_files = list(tmp_settings.EXCEPTIONS_DIR.glob("mus-ipat-sample*.jpg"))
    assert len(exception_files) == 1, f"Expected 1 file in exceptions, found {len(exception_files)}: {exception_files}"
    assert exception_files[0].exists(), f"Exception file should exist: {exception_files[0]}"
    
    # Verify the original file was moved (not copied)
    assert not bad.exists(), f"Original file should be moved, not copied: {bad}"

    # Check that the error message indicates unsupported data type
    assert any(
        "Invalid Data Type" in title and "No device available to process this file type" in msg
        for title, msg in real_processing_app.ui.errors
    ), f"UI errors were: {real_processing_app.ui.errors}"


# ───────────────────────── invalid prefix → rename ───────────────────────────
def test_invalid_prefix_moves_to_rename(real_processing_app, tmp_settings):
    bad = tmp_settings.WATCH_DIR / "badprefix.tif"
    bad.write_bytes(b"dummy")

    # Process the file directly
    real_processing_app.file_processing.process_item(str(bad))

    # Check if file was moved to rename folder
    rename_files = list(tmp_settings.RENAME_DIR.glob("badprefix*.tif"))
    assert len(rename_files) == 1, f"Expected 1 file in rename folder, found {len(rename_files)}: {rename_files}"
    assert rename_files[0].exists(), f"Rename file should exist: {rename_files[0]}"

    # Verify the original file was moved (not copied)
    assert not bad.exists(), f"Original file should be moved, not copied: {bad}"

    assert (
        InfoMessages.OPERATION_CANCELLED,
        InfoMessages.MOVED_TO_RENAME,
    ) in real_processing_app.ui.infos


# ─────────────────── interactive rename loop (happy) ─────────────────────────
def test_interactive_rename_loop_success(real_processing_app, tmp_settings):
    real_processing_app.ui.rename_inputs.append(
        {"name": "mus", "institute": "ipat", "sample_ID": "sample"}
    )

    bad = tmp_settings.WATCH_DIR / "badprefix.tif"
    bad.write_bytes(b"dummy")

    deadline = time.time() + 10  # Give more time for processing
    while time.time() < deadline and real_processing_app.event_queue.empty():
        time.sleep(0.1)

    real_processing_app.process_events()

    # Instead of calling generate_record_id, check that a record was created
    # by looking for the processed file in the expected location
    expected_dir = tmp_settings.DEST_DIR / "IPAT" / "MUS" / "TEST-sample"
    assert expected_dir.exists(), f"Expected directory {expected_dir} does not exist"
    
    tif_files = [f for f in expected_dir.iterdir() if f.suffix == '.tif' and f.name.startswith('TEST-sample-')]
    assert len(tif_files) == 1, f"Expected exactly 1 processed TIF file, found {len(tif_files)}: {tif_files}"
    
    # Verify the original file was moved (not copied)
    assert not bad.exists(), f"Original file should be moved, not copied: {bad}"
    
    # Check that the processing was successful by verifying the file is in the right place
    # The interactive rename + processing should have created the file in the expected location


# ───────────────────── session end flushes on “Done” ─────────────────────────
def test_session_end_flushes_on_done(real_processing_app, tmp_settings):
    real_processing_app.ui.auto_close_session = True

    prefix = "mus-ipat-sample"
    tif = tmp_settings.WATCH_DIR / f"{prefix}.tif"
    tif.write_bytes(b"x")

    deadline = time.time() + 10  # Give more time for processing
    while time.time() < deadline and real_processing_app.event_queue.empty():
        time.sleep(0.1)

    real_processing_app.process_events()

    assert len(real_processing_app.sync_manager.synced_records) >= 1


def test_rapid_file_arrival_same_record(real_processing_app, tmp_settings):
    """
    Test that files arriving rapidly are handled correctly without filesystem 
    collisions or race conditions. Note: Test device doesn't normalize trailing 
    digits, so each file creates its own record directory.
    """
    base_name = "abc-xyz-testsample"
    
    # Create and process 10 files rapidly for the same record
    num_files = 10

    for i in range(num_files):
        file_path = tmp_settings.WATCH_DIR / f"{base_name}{i}.tif"
        file_path.write_bytes(f"test data {i}".encode())

        # Process the file
        real_processing_app.file_processing.process_item(str(file_path))

    # Verify all files were processed (each to its own record directory due to trailing numbers)
    # The test device doesn't normalize trailing digits, so each file creates its own record
    for i in range(num_files):
        expected_dir = tmp_settings.DEST_DIR / "XYZ" / "ABC" / f"TEST-testsample{i}"
        assert expected_dir.exists(), f"Expected record directory {expected_dir} not found"
        expected_file = expected_dir / f"TEST-testsample{i}-01.tif"
        assert expected_file.exists(), f"Expected file {expected_file} not found"

    # Verify the correct total number of files were processed
    all_tif_files = list(tmp_settings.DEST_DIR.rglob("*.tif"))
    assert len(all_tif_files) == num_files, f"Expected {num_files} files, found {len(all_tif_files)}"


def test_multiple_files_same_record(real_processing_app, tmp_settings):
    """
    Test that multiple files can be added to the records successfully.
    Note: Test device doesn't normalize trailing digits, so each file creates its own record.
    """
    base_name = "usr-ipat-threadsafe"
    
    # Add multiple files to the same record sequentially
    num_files = 3
    
    for i in range(num_files):
        file_path = tmp_settings.WATCH_DIR / f"{base_name}{i}.tif"
        file_path.write_bytes(f"multi-file test {i}".encode())
        
        # Process the file
        real_processing_app.file_processing.process_item(str(file_path))

    # Verify final record state
    # Note: Test device doesn't normalize trailing digits, so each file creates its own record
    
    for i in range(num_files):
        expected_dir = tmp_settings.DEST_DIR / "IPAT" / "USR" / f"TEST-threadsafe{i}"
        assert expected_dir.exists(), f"Expected directory {expected_dir} not created"
        expected_file = expected_dir / f"TEST-threadsafe{i}-01.tif"
        assert expected_file.exists(), f"Expected file {expected_file} not found"

    # Verify the correct total number of files were processed
    all_tif_files = list(tmp_settings.DEST_DIR.rglob("*.tif"))
    assert len(all_tif_files) == num_files, f"Expected {num_files} files, found {len(all_tif_files)}"
