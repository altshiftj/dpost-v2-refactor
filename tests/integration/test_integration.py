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
      • FileProcessManager        (real, with TischREM device support)
    """

    ui = HeadlessUI()
    sync = DummySyncManager(ui=ui)

    # Set up SettingsManager with TischREM device for realistic integration testing
    from ipat_watchdog.core.config.settings_store import SettingsStore, SettingsManager
    from ipat_watchdog.pc_plugins.tischrem_blb.settings import PCTischREMSettings
    from ipat_watchdog.device_plugins.sem_phenomxl2.settings import SEMPhenomXL2Settings

    # Override both global and device settings to use test paths for proper isolation
    class IntegrationGlobalSettings(PCTischREMSettings):
        def __init__(self):
            super().__init__()
            # Use the same paths as tmp_settings for proper isolation
            self.APP_DIR = tmp_settings.APP_DIR
            self.WATCH_DIR = tmp_settings.WATCH_DIR
            self.DEST_DIR = tmp_settings.DEST_DIR
            self.RENAME_DIR = tmp_settings.RENAME_DIR
            self.EXCEPTIONS_DIR = tmp_settings.EXCEPTIONS_DIR
            self.DAILY_RECORDS_JSON = tmp_settings.DAILY_RECORDS_JSON

    class IntegrationTischREMSettings(SEMPhenomXL2Settings):
        def __init__(self):
            super().__init__()
            # Override only the paths to use test paths, keep all device-specific settings
            self.APP_DIR = tmp_settings.APP_DIR
            self.WATCH_DIR = tmp_settings.WATCH_DIR
            self.DEST_DIR = tmp_settings.DEST_DIR
            self.RENAME_DIR = tmp_settings.RENAME_DIR
            self.EXCEPTIONS_DIR = tmp_settings.EXCEPTIONS_DIR
            self.DAILY_RECORDS_JSON = tmp_settings.DAILY_RECORDS_JSON
            self.LOG_FILE = tmp_settings.LOG_FILE
            # All other TischREM-specific attributes (DEVICE_RECORD_KADI_ID, etc.) are inherited

    global_settings = IntegrationGlobalSettings()
    tischrem_settings = IntegrationTischREMSettings()
    settings_manager = SettingsManager([tischrem_settings], global_settings)
    SettingsStore.set_manager(settings_manager)
    
    # Set device context to TischREM for proper timeout and other device settings
    settings_manager.set_current_device("sem_phenomxl2")

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
    # TischREM moves files to Data/INSTITUTE/USER/SAMPLE/ structure
    expected_dir = tmp_settings.DEST_DIR / "IPAT" / "MUS" / "sample"
    assert expected_dir.exists(), f"Expected directory {expected_dir} does not exist"
    
    files_in_dir = list(expected_dir.iterdir())
    # Look for a file that starts with "REM-sample-"
    tif_files = [f for f in files_in_dir if f.suffix == '.tif' and f.name.startswith('REM-sample-')]
    assert len(tif_files) == 1, f"Expected exactly 1 processed TIF file, found {len(tif_files)}: {tif_files}"
    assert tif_files[0].exists(), f"Processed file should exist: {tif_files[0]}"
    
    # Verify the original file was moved (not copied)
    assert not tif_path.exists(), f"Original file should be moved, not copied: {tif_path}"


# ───────────────────────── invalid extension test ────────────────────────────
def test_invalid_extension_moves_to_exception(real_processing_app, tmp_settings):
    bad = tmp_settings.WATCH_DIR / "mus-ipat-sample.jpg"
    bad.write_bytes(b"nope")

    # Debug: Print settings information
    print(f"\n=== SETTINGS DEBUG ===")
    print(f"Watch directory: {tmp_settings.WATCH_DIR}")
    print(f"Exceptions directory: {tmp_settings.EXCEPTIONS_DIR}")
    print(f"File created at: {bad}")
    print(f"File exists: {bad.exists()}")
    print(f"App global settings: {real_processing_app.global_settings}")
    print(f"App watch dir: {real_processing_app.watch_dir}")
    print(f"Settings manager current device: {real_processing_app.settings_manager.get_current_device()}")
    print(f"Observer is running: {getattr(real_processing_app.directory_observer, 'is_alive', lambda: 'N/A')()}")
    if hasattr(real_processing_app.directory_observer, 'emitters'):
        emitters = real_processing_app.directory_observer.emitters
        print(f"Observer emitters count: {len(emitters)}")
        for i, emitter in enumerate(emitters):
            print(f"  Emitter {i}: {emitter.watch.path} (recursive: {emitter.watch.is_recursive})")
    if hasattr(real_processing_app, 'file_event_handler'):
        print(f"Handler settings: {getattr(real_processing_app.file_event_handler, 'settings', 'N/A')}")
    print("======================\n")

    # Wait for the file to be detected, queued, and processed
    deadline = time.time() + 10  # Give more time for file stabilization and processing
    processed = False
    while time.time() < deadline:
        # Process any queued events
        real_processing_app.process_events()
        
        # Check if file was moved to exceptions
        if any(tmp_settings.EXCEPTIONS_DIR.glob("mus-ipat-sample*.jpg")):
            processed = True
            break
            
        # Also check if file was queued but not yet processed
        if not real_processing_app.event_queue.empty():
            print(f"DEBUG: File queued, processing...")
            real_processing_app.process_events()
            
        time.sleep(0.1)
    
    if not processed:
        # Debug information
        print(f"DEBUG: Files in WATCH_DIR: {list(tmp_settings.WATCH_DIR.glob('*'))}")
        print(f"DEBUG: Files in EXCEPTIONS_DIR: {list(tmp_settings.EXCEPTIONS_DIR.glob('*'))}")
        print(f"DEBUG: Queue empty: {real_processing_app.event_queue.empty()}")
        pytest.fail("File was never moved to exceptions folder")

    matches = list(tmp_settings.EXCEPTIONS_DIR.glob("mus-ipat-sample*.jpg"))
    assert len(matches) == 1 and matches[0].exists()

    # Check that the error message indicates unsupported data type
    assert any(
        "Invalid Data Type" in title and "No device available to process this file type" in msg
        for title, msg in real_processing_app.ui.errors
    ), f"UI errors were: {real_processing_app.ui.errors}"


# ───────────────────────── invalid prefix → rename ───────────────────────────
def test_invalid_prefix_moves_to_rename(real_processing_app, tmp_settings):
    bad = tmp_settings.WATCH_DIR / "badprefix.tif"
    bad.write_bytes(b"dummy")

    deadline = time.time() + 10  # Give more time for processing
    while time.time() < deadline and real_processing_app.event_queue.empty():
        time.sleep(0.1)

    real_processing_app.process_events()

    matches = list(tmp_settings.RENAME_DIR.glob("badprefix*.tif"))
    assert len(matches) == 1 and matches[0].exists()

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
    expected_dir = tmp_settings.DEST_DIR / "IPAT" / "MUS" / "sample"
    assert expected_dir.exists(), f"Expected directory {expected_dir} does not exist"
    
    tif_files = [f for f in expected_dir.iterdir() if f.suffix == '.tif' and f.name.startswith('REM-sample-')]
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
    Test that files arriving rapidly for the same record are handled correctly
    without filesystem collisions or race conditions.
    """
    base_name = "abc-xyz-testsample"
    
    # Create and process 10 files rapidly for the same record
    num_files = 10
    
    for i in range(num_files):
        file_path = tmp_settings.WATCH_DIR / f"{base_name}{i}.tif"
        file_path.write_bytes(f"test data {i}".encode())
        
        # Process the file
        real_processing_app.file_processing.process_item(str(file_path))

    # Verify all files were processed into the same record directory
    expected_dir = tmp_settings.DEST_DIR / "XYZ" / "ABC" / "testsample"
    assert expected_dir.exists(), f"Expected record directory {expected_dir} not found"
    
    # Check all files are present with unique names
    processed_files = [f for f in expected_dir.iterdir() if f.suffix == '.tif']
    assert len(processed_files) == num_files, \
        f"Expected {num_files} files, found {len(processed_files)}: {processed_files}"
    
    # Verify unique naming - each should have incremental suffix
    file_names = sorted([f.name for f in processed_files])
    for i, name in enumerate(file_names, 1):
        expected_suffix = f"-{i:02d}.tif"
        assert name.endswith(expected_suffix), \
            f"File {name} doesn't have expected suffix {expected_suffix}"


def test_multiple_files_same_record(real_processing_app, tmp_settings):
    """
    Test that multiple files can be added to the same record successfully.
    Tests sequential processing of multi-file records.
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
    # Files with trailing digits get normalized (usr-ipat-threadsafe0 -> usr-ipat-threadsafe)
    # And usr-ipat maps to IPAT/USR directory structure
    expected_dir = tmp_settings.DEST_DIR / "IPAT" / "USR" / "threadsafe"
    assert expected_dir.exists(), f"Expected directory {expected_dir} not created"
    
    processed_files = [f for f in expected_dir.iterdir() if f.suffix == '.tif']
    assert len(processed_files) == num_files, \
        f"Expected {num_files} files, found {len(processed_files)}: {processed_files}"
    
    # Verify record manager state is consistent (check before app shutdown)
    from ipat_watchdog.core.config.settings_store import SettingsStore
    
    settings = SettingsStore.get()
    sanitized_prefix = f"usr{settings.ID_SEP}ipat{settings.ID_SEP}threadsafe"
    # Use hardcoded TischREM record ID for this test
    record_id = f"rem_01{settings.ID_SEP}{sanitized_prefix}".lower()
    
    record_manager = real_processing_app.file_processing.records
    record = record_manager.get_record_by_id(record_id)
    
    assert record is not None, f"Record {record_id} not found in record manager"
    assert len(record.files_uploaded) == num_files, \
        f"Record shows {len(record.files_uploaded)} files, expected {num_files}"
