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
    from ipat_watchdog.core.config.pc_settings import PCSettings
    from ipat_watchdog.device_plugins.sem_phenomxl2.settings import SEMPhenomXL2Settings
    from ipat_watchdog.device_plugins.utm_zwick_blb.settings import SettingsZwickUTM

    # Override global and device settings to use test paths
    class IntegrationGlobalSettings(PCSettings):
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

    class IntegrationTischREMSettings(SEMPhenomXL2Settings):
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
    settings_manager = SettingsManager([tischrem_settings, utm_settings], global_settings)
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

    # Debug: Check initial state
    print(f"DEBUG: Created file at: {tif_path}")
    print(f"DEBUG: File exists: {tif_path.exists()}")
    print(f"DEBUG: DEST_DIR: {tmp_settings.DEST_DIR}")
    
    # Process the file directly instead of waiting for file watcher
    try:
        multi_device_app.file_processing.process_item(str(tif_path))
        print("DEBUG: process_item completed successfully")
    except Exception as e:
        print(f"DEBUG: process_item failed with error: {e}")
        raise

    # Debug: Check what directories were created
    print(f"DEBUG: DEST_DIR contents: {list(tmp_settings.DEST_DIR.iterdir()) if tmp_settings.DEST_DIR.exists() else 'DEST_DIR does not exist'}")
    
    # Check TischREM-specific processing: files go to INSTITUTE/USER/SAMPLE structure
    expected_dir = tmp_settings.DEST_DIR / "IPAT" / "MUS" / "sample"
    print(f"DEBUG: Looking for directory: {expected_dir}")
    
    if not expected_dir.exists():
        # Let's check what's actually in the dest dir
        if tmp_settings.DEST_DIR.exists():
            def print_tree(path, prefix=""):
                for item in path.iterdir():
                    print(f"DEBUG: {prefix}{item.name}")
                    if item.is_dir():
                        print_tree(item, prefix + "  ")
            print_tree(tmp_settings.DEST_DIR)
    
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

    # Process both files directly
    multi_device_app.file_processing.process_item(str(xlsx_path))
    multi_device_app.file_processing.process_item(str(zs2_path))

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

    # Process the file directly
    multi_device_app.file_processing.process_item(str(unsupported_path))

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

    # Process files directly
    multi_device_app.file_processing.process_item(str(tif_path))
    multi_device_app.file_processing.process_item(str(xlsx_path))
    multi_device_app.file_processing.process_item(str(zs2_path))

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
    
    zs2_path.write_bytes(b"UTM raw data")
    xlsx_path.write_bytes(b"UTM Excel data")

    # Process both files directly
    multi_device_app.file_processing.process_item(str(zs2_path))
    multi_device_app.file_processing.process_item(str(xlsx_path))

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
        if device.get_device_id() == "sem_phenomxl2":
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


def test_tischrem_same_name_files_get_unique_names(multi_device_app, tmp_settings):
    """
    Test that multiple TischREM files with the same base name receive unique 
    incremental names and are placed in the correct folder structure.
    """
    # TischREM device always produces "sample1.tif" since processed files are moved away
    # Test multiple such files arriving (e.g., network delays, buffering, etc.)
    base_name = "mus-ipat-sample1"  # Device always adds "1"
    
    # Create 5 files with same name to test unique naming
    for i in range(5):
        # Create in temporary subdirectories to avoid filesystem conflicts during test setup
        temp_dir = tmp_settings.WATCH_DIR / f"temp{i}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        file_path = temp_dir / f"{base_name}.tif"
        file_path.write_bytes(f"dummy TischREM image data {i}".encode())
        
        # Process each file
        multi_device_app.file_processing.process_item(str(file_path))

    # Verify all files were processed and placed correctly
    # After preprocessing, files should all target the same base record "sample"
    # but may end up in separate directories due to collision handling
    base_dir = tmp_settings.DEST_DIR / "IPAT" / "MUS"
    assert base_dir.exists(), f"Base directory {base_dir} was not created"
    
    # Check that files were processed (may be in sample_0, sample_1, etc. subdirs due to collisions)
    processed_files = []
    for subdir in base_dir.iterdir():
        if subdir.is_dir() and subdir.name.startswith('sample'):
            for f in subdir.iterdir():
                if f.suffix == '.tif' and 'REM-' in f.name:
                    processed_files.append(f)
    
    assert len(processed_files) == 5, f"Expected 5 processed files, found {len(processed_files)}: {processed_files}"
    
    # Verify files have unique incremental names
    file_names = [f.name for f in processed_files]
    # Files should have REM-sample*-NN.tif pattern with unique increments
    rem_pattern_count = sum(1 for name in file_names if name.startswith('REM-sample') and name.endswith('.tif'))
    assert rem_pattern_count == 5, f"Expected 5 files with REM-sample pattern, got {rem_pattern_count}: {file_names}"


def test_tischrem_different_device_groups_no_collision(multi_device_app, tmp_settings):
    """
    Test that TischREM files for different user/institute groups don't interfere
    with each other's naming or folder structure.
    """
    test_files = [
        ("mus-ipat-sample1", "mus", "ipat", "sample1"),
        ("abc-xyz-sample2", "abc", "xyz", "sample2"),
        ("def-uvw-sample3", "def", "uvw", "sample3"),
    ]
    
    expected_dirs = []
    
    # Process files sequentially
    for filename, user, institute, sample in test_files:
        file_path = tmp_settings.WATCH_DIR / f"{filename}.tif"
        file_path.write_bytes(f"data for {filename}".encode())

        multi_device_app.file_processing.process_item(str(file_path))

        # Calculate expected directory
        # TischREM processor removes trailing digits, so sample1/sample2/sample3 all become "sample"
        normalized_sample = sample[:-1] if sample and sample[-1].isdigit() else sample
        expected_dir = str(tmp_settings.DEST_DIR / institute.upper() / user.upper() / normalized_sample)
        expected_dirs.append(expected_dir)

    # Verify each file group created its own directory structure
    for expected_dir in expected_dirs:
        dir_path = Path(expected_dir)
        assert dir_path.exists(), f"Expected directory {dir_path} was not created"
        
        # Verify exactly one file in each directory
        tif_files = [f for f in dir_path.iterdir() if f.suffix == '.tif']
        assert len(tif_files) == 1, \
            f"Expected 1 file in {dir_path}, found {len(tif_files)}: {tif_files}"


def test_multiple_device_files_processed_to_correct_destinations(multi_device_app, tmp_settings):
    """
    Test that files from different devices (TischREM and UTM) arriving in mixed order
    are correctly routed to their appropriate device processors and destination folders.
    """
    # Create files for both device types with mixed naming patterns
    tischrem_file1 = tmp_settings.WATCH_DIR / "mus-ipat-sample1.tif"
    tischrem_file2 = tmp_settings.WATCH_DIR / "abc-xyz-test2.tif"
    
    # UTM requires paired files (.xlsx + .zs2)
    utm_xlsx = tmp_settings.WATCH_DIR / "def-uvw-utmtest.xlsx"
    utm_zs2 = tmp_settings.WATCH_DIR / "def-uvw-utmtest.zs2"
    
    # Create file contents
    tischrem_file1.write_bytes(b"TischREM image data 1")
    tischrem_file2.write_bytes(b"TischREM image data 2") 
    utm_xlsx.write_bytes(b"UTM Excel data")
    utm_zs2.write_bytes(b"UTM raw measurement data")
    
    # Process files in mixed order to test device routing
    multi_device_app.file_processing.process_item(str(tischrem_file1))
    multi_device_app.file_processing.process_item(str(utm_xlsx))  # Only one UTM file first
    multi_device_app.file_processing.process_item(str(tischrem_file2))
    multi_device_app.file_processing.process_item(str(utm_zs2))   # Complete UTM pair
    
    # Verify TischREM files went to correct locations
    tischrem_dir1 = tmp_settings.DEST_DIR / "IPAT" / "MUS" / "sample"
    tischrem_dir2 = tmp_settings.DEST_DIR / "XYZ" / "ABC" / "test"
    
    assert tischrem_dir1.exists(), f"TischREM directory 1 {tischrem_dir1} not created"
    assert tischrem_dir2.exists(), f"TischREM directory 2 {tischrem_dir2} not created"
    
    # Check TischREM files exist and have correct naming pattern
    tischrem_files1 = [f for f in tischrem_dir1.iterdir() if f.suffix == '.tif' and 'REM-sample' in f.name]
    tischrem_files2 = [f for f in tischrem_dir2.iterdir() if f.suffix == '.tif' and 'REM-test' in f.name]
    
    assert len(tischrem_files1) == 1, f"Expected 1 TischREM file in dir1, got {len(tischrem_files1)}: {tischrem_files1}"
    assert len(tischrem_files2) == 1, f"Expected 1 TischREM file in dir2, got {len(tischrem_files2)}: {tischrem_files2}"
    
    # Verify UTM files went to correct location (UVW/DEF structure)
    utm_dir = tmp_settings.DEST_DIR / "UVW" / "DEF" / "utmtest"
    assert utm_dir.exists(), f"UTM directory {utm_dir} not created"
    
    # Check UTM files exist and have correct processing (Excel + ZIP of raw data)
    utm_xlsx_files = [f for f in utm_dir.iterdir() if f.suffix == '.xlsx']
    utm_zip_files = [f for f in utm_dir.iterdir() if f.name.endswith('.zs2.zip')]
    
    assert len(utm_xlsx_files) == 1, f"Expected 1 UTM Excel file, got {len(utm_xlsx_files)}: {utm_xlsx_files}"
    assert len(utm_zip_files) == 1, f"Expected 1 UTM ZIP file, got {len(utm_zip_files)}: {utm_zip_files}"
    
    # Verify all original files were processed (moved/consumed)
    assert not tischrem_file1.exists(), "TischREM file 1 should be moved"
    assert not tischrem_file2.exists(), "TischREM file 2 should be moved" 
    assert not utm_xlsx.exists(), "UTM Excel file should be moved"
    assert not utm_zs2.exists(), "UTM raw file should be processed"
    
    # Verify device-specific naming patterns
    tischrem_file1_processed = tischrem_files1[0]
    tischrem_file2_processed = tischrem_files2[0]
    utm_xlsx_processed = utm_xlsx_files[0]
    
    assert tischrem_file1_processed.name.startswith('REM-sample-'), f"TischREM file 1 has wrong naming: {tischrem_file1_processed.name}"
    assert tischrem_file2_processed.name.startswith('REM-test-'), f"TischREM file 2 has wrong naming: {tischrem_file2_processed.name}"
    assert utm_xlsx_processed.name.startswith('UTM-utmtest-'), f"UTM file has wrong naming: {utm_xlsx_processed.name}"
