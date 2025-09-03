from __future__ import annotations

import time
import os
from pathlib import Path

import pytest
from watchdog.observers.polling import PollingObserver

from ipat_watchdog.core.app.device_watchdog_app import DeviceWatchdogApp
from ipat_watchdog.core.processing.file_process_manager import FileProcessManager
from ipat_watchdog.core.storage.filesystem_utils import init_dirs
from tests.helpers.fake_sync import DummySyncManager
from tests.helpers.fake_ui import HeadlessUI


# ────────────────────────── fixtures ──────────────────────────────────────────
@pytest.fixture
def multi_device_app(tmp_settings):
    """
    Build DeviceWatchdogApp with both TischREM and UTM device support.
    Tests that file routing works correctly when multiple devices are available.
    """

    ui = HeadlessUI()
    sync = DummySyncManager(ui=ui)

    # Set up SettingsManager with both TischREM and UTM devices
    from ipat_watchdog.core.config.settings_store import SettingsStore, SettingsManager
    from ipat_watchdog.core.config.global_settings import GlobalSettings
    from ipat_watchdog.device_plugins.sem_tischrem_blb.settings import TischREMSettings
    from ipat_watchdog.device_plugins.utm_zwick_blb.settings import SettingsZwickUTM

    # Override global and device settings to use test paths
    class IntegrationGlobalSettings(GlobalSettings):
        def __init__(self):
            super().__init__()
            self.APP_DIR = tmp_settings.APP_DIR
            self.WATCH_DIR = tmp_settings.WATCH_DIR
            self.DEST_DIR = tmp_settings.DEST_DIR
            self.RENAME_DIR = tmp_settings.RENAME_DIR
            self.EXCEPTIONS_DIR = tmp_settings.EXCEPTIONS_DIR
            self.DAILY_RECORDS_JSON = tmp_settings.DAILY_RECORDS_JSON
            # Set reasonable defaults for multi-device scenarios
            self.MAX_WAIT_SECONDS = 30.0
            self.POLL_SECONDS = 1.0

    class IntegrationTischREMSettings(TischREMSettings):
        def __init__(self):
            super().__init__()
            # Override paths to use test paths, keep device-specific settings
            self.APP_DIR = tmp_settings.APP_DIR
            self.WATCH_DIR = tmp_settings.WATCH_DIR
            self.DEST_DIR = tmp_settings.DEST_DIR
            self.RENAME_DIR = tmp_settings.RENAME_DIR
            self.EXCEPTIONS_DIR = tmp_settings.EXCEPTIONS_DIR
            self.DAILY_RECORDS_JSON = tmp_settings.DAILY_RECORDS_JSON
            self.LOG_FILE = tmp_settings.LOG_FILE

    class IntegrationUTMSettings(SettingsZwickUTM):
        def __init__(self):
            super().__init__()
            # Override paths to use test paths, keep device-specific settings
            self.APP_DIR = tmp_settings.APP_DIR
            self.WATCH_DIR = tmp_settings.WATCH_DIR
            self.DEST_DIR = tmp_settings.DEST_DIR
            self.RENAME_DIR = tmp_settings.RENAME_DIR
            self.EXCEPTIONS_DIR = tmp_settings.EXCEPTIONS_DIR
            self.DAILY_RECORDS_JSON = tmp_settings.DAILY_RECORDS_JSON
            self.LOG_FILE = tmp_settings.LOG_FILE

    global_settings = IntegrationGlobalSettings()
    tischrem_settings = IntegrationTischREMSettings()
    utm_settings = IntegrationUTMSettings()
    
    # Register both devices
    settings_manager = SettingsManager(global_settings, [tischrem_settings, utm_settings])
    SettingsStore.set_manager(settings_manager)

    # Create directories using the proper settings
    init_dirs()

    app = DeviceWatchdogApp(
        ui=ui,
        sync_manager=sync,
        settings_manager=settings_manager,
        observer_cls=PollingObserver,
        file_process_manager_cls=FileProcessManager,
    )

    app.initialize()
    yield app
    app.on_closing()


# ───────────────────────── Multi-Device Integration Tests ─────────────────────────────────
def test_tischrem_file_processed_correctly(multi_device_app, tmp_settings):
    """Test that TischREM files (.tif) are processed by the TischREM processor."""
    prefix = "mus-ipat-sample"
    tif_path = tmp_settings.WATCH_DIR / f"{prefix}.tif"
    tif_path.write_bytes(b"dummy TischREM image")

    # Wait for file detection and processing
    deadline = time.time() + 10
    while time.time() < deadline and multi_device_app.event_queue.empty():
        time.sleep(0.1)

    multi_device_app.process_events()

    # Check TischREM-specific processing: files go to INSTITUTE/USER/SAMPLE structure
    expected_dir = tmp_settings.DEST_DIR / "IPAT" / "MUS" / "sample"
    assert expected_dir.exists(), f"TischREM expected directory {expected_dir} does not exist"
    
    tif_files = [f for f in expected_dir.iterdir() if f.suffix == '.tif' and f.name.startswith('REM-sample-')]
    assert len(tif_files) == 1, f"Expected exactly 1 TischREM processed file, found {len(tif_files)}: {tif_files}"
    
    # Verify original file was moved
    assert not tif_path.exists(), f"Original TischREM file should be moved: {tif_path}"


def test_utm_file_processed_correctly(multi_device_app, tmp_settings):
    """Test that UTM files (.xlsx + .zs2 pair) are processed by the UTM processor."""
    prefix = "mus-ipat-sample"
    
    # UTM processor expects both files to be present
    xlsx_path = tmp_settings.WATCH_DIR / f"{prefix}.xlsx"
    zs2_path = tmp_settings.WATCH_DIR / f"{prefix}.zs2"
    
    xlsx_path.write_bytes(b"dummy UTM Excel data")
    zs2_path.write_bytes(b"dummy UTM raw data")

    # Wait for file detection and processing
    deadline = time.time() + 10
    while time.time() < deadline and multi_device_app.event_queue.empty():
        time.sleep(0.1)

    multi_device_app.process_events()

    # Check UTM-specific processing: files go to INSTITUTE/USER/SAMPLE structure
    expected_dir = tmp_settings.DEST_DIR / "IPAT" / "MUS" / "sample"
    assert expected_dir.exists(), f"UTM expected directory {expected_dir} does not exist"
    
    # UTM processor creates .xlsx file and .zs2.zip file
    xlsx_files = [f for f in expected_dir.iterdir() if f.suffix == '.xlsx']
    zip_files = [f for f in expected_dir.iterdir() if f.name.endswith('.zs2.zip')]
    
    assert len(xlsx_files) == 1, f"Expected exactly 1 UTM Excel file, found {len(xlsx_files)}: {xlsx_files}"
    assert len(zip_files) == 1, f"Expected exactly 1 UTM ZIP file, found {len(zip_files)}: {zip_files}"
    
    # Verify original files were moved
    assert not xlsx_path.exists(), f"Original UTM Excel file should be moved: {xlsx_path}"
    assert not zs2_path.exists(), f"Original UTM zs2 file should be moved: {zs2_path}"


def test_unsupported_file_rejected(multi_device_app, tmp_settings):
    """Test that files not supported by any device are moved to exceptions."""
    unsupported_path = tmp_settings.WATCH_DIR / "mus-ipat-sample.pdf"
    unsupported_path.write_bytes(b"unsupported file type")

    # Wait for file detection and processing
    deadline = time.time() + 10
    while time.time() < deadline and multi_device_app.event_queue.empty():
        time.sleep(0.1)

    multi_device_app.process_events()

    # Check that file was moved to exceptions
    exception_files = list(tmp_settings.EXCEPTIONS_DIR.glob("mus-ipat-sample*.pdf"))
    assert len(exception_files) == 1, f"Expected 1 file in exceptions, found {len(exception_files)}: {exception_files}"
    
    # Check UI error message (should show unsupported data type)
    assert len(multi_device_app.ui.errors) > 0, f"Expected error messages, but got none"
    error_titles = [title for title, msg in multi_device_app.ui.errors]
    assert any("Invalid Data Type" in title or "Unsupported" in title for title in error_titles), f"Expected unsupported error, got: {multi_device_app.ui.errors}"


def test_device_routing_by_extension(multi_device_app, tmp_settings):
    """Test that files are routed to the correct device based on extension."""
    # Create files for both devices
    tif_path = tmp_settings.WATCH_DIR / "mus-ipat-tischrem.tif"
    # UTM requires both files for processing
    xlsx_path = tmp_settings.WATCH_DIR / "mus-ipat-utm.xlsx"
    zs2_path = tmp_settings.WATCH_DIR / "mus-ipat-utm.zs2"
    
    tif_path.write_bytes(b"TischREM image")
    xlsx_path.write_bytes(b"UTM Excel data")
    zs2_path.write_bytes(b"UTM raw data")

    # Wait for file detection and processing
    deadline = time.time() + 15  # Give extra time for all files
    processed_count = 0
    while time.time() < deadline and processed_count < 2:  # TischREM=1 + UTM=1 record
        multi_device_app.process_events()
        
        # Count processed files
        expected_dir = tmp_settings.DEST_DIR / "IPAT" / "MUS"
        if expected_dir.exists():
            tischrem_files = list(expected_dir.glob("tischrem/REM-tischrem-*.tif"))
            utm_xlsx_files = list(expected_dir.glob("utm/UTM-utm-*.xlsx"))
            processed_count = len(tischrem_files) + len(utm_xlsx_files)
        
        time.sleep(0.1)

    # Verify both files were processed by their respective devices
    expected_base = tmp_settings.DEST_DIR / "IPAT" / "MUS"
    
    # Check TischREM file
    tischrem_dir = expected_base / "tischrem"
    assert tischrem_dir.exists(), f"TischREM directory {tischrem_dir} not found"
    tischrem_files = [f for f in tischrem_dir.iterdir() if f.suffix == '.tif' and 'REM-tischrem-' in f.name]
    assert len(tischrem_files) == 1, f"Expected 1 TischREM file, found {len(tischrem_files)}: {tischrem_files}"
    
    # Check UTM files  
    utm_dir = expected_base / "utm"
    assert utm_dir.exists(), f"UTM directory {utm_dir} not found"
    utm_xlsx_files = [f for f in utm_dir.iterdir() if f.suffix == '.xlsx']
    utm_zip_files = [f for f in utm_dir.iterdir() if f.name.endswith('.zs2.zip')]
    assert len(utm_xlsx_files) == 1, f"Expected 1 UTM Excel file, found {len(utm_xlsx_files)}: {utm_xlsx_files}"
    assert len(utm_zip_files) == 1, f"Expected 1 UTM ZIP file, found {len(utm_zip_files)}: {utm_zip_files}"
    
    # Verify originals were processed
    assert not tif_path.exists(), "TischREM file should be moved"
    assert not xlsx_path.exists(), "UTM Excel file should be moved"
    assert not zs2_path.exists(), "UTM raw file should be processed"


def test_utm_twin_file_handling(multi_device_app, tmp_settings):
    """Test UTM's special twin-file handling (.zs2 + .xlsx pairs)."""
    prefix = "mus-ipat-sample"
    
    # Create both files that UTM expects as a pair
    zs2_path = tmp_settings.WATCH_DIR / f"{prefix}.zs2"
    xlsx_path = tmp_settings.WATCH_DIR / f"{prefix}.xlsx"
    
    # Create the first file
    zs2_path.write_bytes(b"UTM raw data")
    
    # Wait a bit, then create the second file
    time.sleep(0.5)
    xlsx_path.write_bytes(b"UTM Excel data")

    # Wait for both files to be detected and processed together
    deadline = time.time() + 15
    while time.time() < deadline and multi_device_app.event_queue.empty():
        time.sleep(0.1)

    multi_device_app.process_events()

    # Check that both files were processed together
    expected_dir = tmp_settings.DEST_DIR / "IPAT" / "MUS" / "sample"
    assert expected_dir.exists(), f"UTM expected directory {expected_dir} does not exist"
    
    # Should have the Excel file and a ZIP of the zs2 file
    xlsx_files = [f for f in expected_dir.iterdir() if f.suffix == '.xlsx']
    zip_files = [f for f in expected_dir.iterdir() if f.name.endswith('.zs2.zip')]
    
    assert len(xlsx_files) == 1, f"Expected 1 Excel file, found {len(xlsx_files)}: {xlsx_files}"
    assert len(zip_files) == 1, f"Expected 1 ZIP file, found {len(zip_files)}: {zip_files}"
    
    # Verify both original files were processed
    assert not zs2_path.exists(), "Original .zs2 file should be processed"
    assert not xlsx_path.exists(), "Original .xlsx file should be processed"


def test_device_context_switching(multi_device_app, tmp_settings):
    """Test that device context can be switched between devices."""
    from ipat_watchdog.core.config.settings_store import SettingsStore
    
    settings_manager = SettingsStore.get_manager()
    
    # Test switching to TischREM
    tischrem_device = None
    utm_device = None
    for device in settings_manager.get_all_devices():
        if device.get_device_id() == "sem_tischrem_blb":
            tischrem_device = device
        elif device.get_device_id() == "utm_zwick_blb":
            utm_device = device
    
    assert tischrem_device is not None, "TischREM device should be available"
    assert utm_device is not None, "UTM device should be available"
    
    # Test switching to TischREM
    settings_manager.set_current_device(tischrem_device)
    current_settings = SettingsStore.get()
    assert current_settings.DEVICE_TYPE == "REM", "Should be using TischREM settings"
    
    # Test switching to UTM
    settings_manager.set_current_device(utm_device)
    current_settings = SettingsStore.get()
    assert current_settings.DEVICE_TYPE == "UTM", "Should be using UTM settings"
    
    # Test invalid device lookup (device not found in manager)
    fake_device_id = "invalid_device"
    selected_device = settings_manager.select_device_for_file(f"test.{fake_device_id}")
    assert selected_device is None, f"Should not find device for fake extension: {selected_device}"
