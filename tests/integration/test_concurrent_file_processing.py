"""
Integration tests for concurrent file processing scenarios.

Tests that verify the system correctly handles multiple files being processed
simultaneously, especially focusing on:
- File naming collision detection and resolution
- Thread-safe record management
- Proper folder structure creation under concurrent load
- Multi-device file routing under concurrent conditions
"""
from __future__ import annotations

import time
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import pytest

from ipat_watchdog.core.app.device_watchdog_app import DeviceWatchdogApp
from ipat_watchdog.core.processing.file_process_manager import FileProcessManager
from ipat_watchdog.core.storage.filesystem_utils import init_dirs
from tests.helpers.fake_sync import DummySyncManager
from tests.helpers.fake_ui import HeadlessUI


@pytest.fixture
def concurrent_test_app(tmp_settings):
    """
    Build DeviceWatchdogApp for concurrent processing tests.
    Uses real FileProcessManager and TischREM device for realistic testing.
    """
    ui = HeadlessUI()
    sync = DummySyncManager(ui=ui)

    # Set up SettingsManager with TischREM device for testing
    from ipat_watchdog.core.config.settings_store import SettingsStore, SettingsManager
    from ipat_watchdog.core.config.global_settings import GlobalSettings
    from ipat_watchdog.device_plugins.sem_tischrem_blb.settings import TischREMSettings

    class ConcurrentGlobalSettings(GlobalSettings):
        def __init__(self):
            super().__init__()
            self.APP_DIR = tmp_settings.APP_DIR
            self.WATCH_DIR = tmp_settings.WATCH_DIR
            self.DEST_DIR = tmp_settings.DEST_DIR
            self.RENAME_DIR = tmp_settings.RENAME_DIR
            self.EXCEPTIONS_DIR = tmp_settings.EXCEPTIONS_DIR
            self.DAILY_RECORDS_JSON = tmp_settings.DAILY_RECORDS_JSON
            # Reduce timers for faster testing
            self.MAX_WAIT_SECONDS = 10.0
            self.POLL_SECONDS = 0.5

    class ConcurrentTischREMSettings(TischREMSettings):
        def __init__(self):
            super().__init__()
            self.APP_DIR = tmp_settings.APP_DIR
            self.WATCH_DIR = tmp_settings.WATCH_DIR
            self.DEST_DIR = tmp_settings.DEST_DIR
            self.RENAME_DIR = tmp_settings.RENAME_DIR
            self.EXCEPTIONS_DIR = tmp_settings.EXCEPTIONS_DIR
            self.DAILY_RECORDS_JSON = tmp_settings.DAILY_RECORDS_JSON
            self.LOG_FILE = tmp_settings.LOG_FILE

    global_settings = ConcurrentGlobalSettings()
    tischrem_settings = ConcurrentTischREMSettings()
    
    settings_manager = SettingsManager(global_settings, [tischrem_settings])
    SettingsStore.set_manager(settings_manager)

    # Create directories
    init_dirs()

    app = DeviceWatchdogApp(
        ui=ui,
        sync_manager=sync,
        settings_manager=settings_manager,
        file_process_manager_cls=FileProcessManager,  # Use real process manager
    )

    app.initialize()
    yield app
    app.on_closing()


def test_concurrent_same_name_files_get_unique_names(concurrent_test_app, tmp_settings):
    """
    Test that multiple files with the same base name processed concurrently
    receive unique incremental names and are placed in the correct folder structure.
    """
    # Create multiple files to simulate concurrent arrival of same-named files
    # In reality, TischREM device always produces "sample1.tif" since processed files are moved away
    # We simulate multiple such files arriving concurrently (e.g., network delays, buffering, etc.)
    base_name = "mus-ipat-sample1"  # Device always adds "1"
    file_paths = []
    
    # Create 5 files with same name but in separate temp locations to simulate concurrent arrival
    for i in range(5):
        # Create in temporary subdirectories to avoid filesystem conflicts during test setup
        temp_dir = tmp_settings.WATCH_DIR / f"temp{i}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        file_path = temp_dir / f"{base_name}.tif"
        file_path.write_bytes(f"dummy TischREM image data {i}".encode())
        file_paths.append(str(file_path))

    # Process files concurrently using threads
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Submit all files for processing simultaneously
        futures = [
            executor.submit(concurrent_test_app.file_processing.process_item, path)
            for path in file_paths
        ]
        
        # Wait for all processing to complete
        for future in as_completed(futures, timeout=30):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                pytest.fail(f"File processing failed with error: {e}")

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
    
    # Verify no original files remain
    for path in file_paths:
        assert not Path(path).exists(), f"Original file should be moved: {path}"


def test_rapid_file_arrival_same_record(concurrent_test_app, tmp_settings):
    """
    Test that files arriving rapidly for the same record are handled correctly
    without filesystem collisions or race conditions.
    """
    base_name = "abc-xyz-testsample"
    
    def create_and_process_file(file_index: int) -> str:
        """Create a file and process it, returning the result path."""
        file_path = tmp_settings.WATCH_DIR / f"{base_name}{file_index}.tif"
        file_path.write_bytes(f"test data {file_index}".encode())
        
        # Process the file
        concurrent_test_app.file_processing.process_item(str(file_path))
        
        return str(file_path)

    # Simulate rapid file arrival (10 files arriving nearly simultaneously)
    num_files = 10
    results = []
    
    with ThreadPoolExecutor(max_workers=num_files) as executor:
        futures = [
            executor.submit(create_and_process_file, i) 
            for i in range(num_files)
        ]
        
        for future in as_completed(futures, timeout=30):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                pytest.fail(f"Rapid file processing failed: {e}")

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


def test_concurrent_different_devices_no_collision(concurrent_test_app, tmp_settings):
    """
    Test that files for different devices processed concurrently don't interfere
    with each other's naming or folder structure.
    """
    # This test requires multi-device setup, but our fixture only has TischREM
    # So we'll test multiple users/institutes instead to verify directory isolation
    
    test_files = [
        ("mus-ipat-sample1", "mus", "ipat", "sample1"),
        ("abc-xyz-sample2", "abc", "xyz", "sample2"),
        ("def-uvw-sample3", "def", "uvw", "sample3"),
    ]
    
    def process_file_group(file_info: tuple) -> str:
        """Process a file and return its expected directory."""
        filename, user, institute, sample = file_info
        file_path = tmp_settings.WATCH_DIR / f"{filename}.tif"
        file_path.write_bytes(f"data for {filename}".encode())

        concurrent_test_app.file_processing.process_item(str(file_path))

        # Return expected directory for verification  
        # TischREM processor removes trailing digits, so sample1/sample2/sample3 all become "sample"
        normalized_sample = sample[:-1] if sample and sample[-1].isdigit() else sample
        return str(tmp_settings.DEST_DIR / institute.upper() / user.upper() / normalized_sample)

    # Process files concurrently
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(process_file_group, file_info)
            for file_info in test_files
        ]
        
        expected_dirs = []
        for future in as_completed(futures, timeout=20):
            try:
                expected_dir = future.result()
                expected_dirs.append(expected_dir)
            except Exception as e:
                pytest.fail(f"Multi-group processing failed: {e}")

    # Verify each file group created its own directory structure
    for expected_dir in expected_dirs:
        dir_path = Path(expected_dir)
        assert dir_path.exists(), f"Expected directory {dir_path} was not created"
        
        # Verify exactly one file in each directory
        tif_files = [f for f in dir_path.iterdir() if f.suffix == '.tif']
        assert len(tif_files) == 1, \
            f"Expected 1 file in {dir_path}, found {len(tif_files)}: {tif_files}"


def test_filesystem_collision_resolution(concurrent_test_app, tmp_settings):
    """
    Test that the get_unique_filename function correctly resolves filename
    collisions even under concurrent access patterns.
    """
    from ipat_watchdog.core.storage.filesystem_utils import get_unique_filename
    
    # Create a test directory
    test_dir = tmp_settings.DEST_DIR / "collision_test"
    test_dir.mkdir(parents=True, exist_ok=True)
    
    base_name = "test-file"
    extension = ".txt"
    
    def create_unique_file(thread_id: int) -> str:
        """Create a file with unique name in the test directory."""
        unique_path = get_unique_filename(str(test_dir), base_name, extension)
        
        # Create the file to claim the name
        Path(unique_path).write_text(f"content from thread {thread_id}")
        
        return unique_path

    # Run multiple threads trying to create files with the same base name
    num_threads = 20
    created_files = []
    
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [
            executor.submit(create_unique_file, i) 
            for i in range(num_threads)
        ]
        
        for future in as_completed(futures, timeout=15):
            try:
                file_path = future.result()
                created_files.append(file_path)
            except Exception as e:
                pytest.fail(f"Unique filename generation failed: {e}")

    # Verify all files were created with unique names
    assert len(created_files) == num_threads, \
        f"Expected {num_threads} files, got {len(created_files)}"
    
    assert len(set(created_files)) == num_threads, \
        f"Files don't have unique names: {created_files}"
    
    # Verify all files actually exist
    for file_path in created_files:
        assert Path(file_path).exists(), f"File {file_path} was not created"
        
    # Verify naming pattern - should be test-file-01.txt, test-file-02.txt, etc.
    file_numbers = []
    for file_path in created_files:
        name = Path(file_path).name
        # Extract number from name like "test-file-01.txt"
        if name.startswith("test-file-") and name.endswith(".txt"):
            number_part = name[10:-4]  # Remove "test-file-" and ".txt"
            try:
                file_numbers.append(int(number_part))
            except ValueError:
                pytest.fail(f"Unexpected filename format: {name}")
    
    # Should have consecutive numbers from 1 to num_threads
    expected_numbers = list(range(1, num_threads + 1))
    assert sorted(file_numbers) == expected_numbers, \
        f"File numbers {sorted(file_numbers)} don't match expected {expected_numbers}"


def test_record_thread_safety(concurrent_test_app, tmp_settings):
    """
    Test that the record management system is thread-safe when multiple
    files are being added to the same record simultaneously.
    """
    base_name = "usr-ipat-threadsafe"
    
    def add_file_to_record(file_index: int) -> bool:
        """Add a file to the record and return success status."""
        try:
            file_path = tmp_settings.WATCH_DIR / f"{base_name}{file_index}.tif"
            file_path.write_bytes(f"thread safety test {file_index}".encode())
            
            # Process the file
            concurrent_test_app.file_processing.process_item(str(file_path))
            return True
        except Exception as e:
            print(f"Thread {file_index} failed: {e}")
            return False

    # Add multiple files to the same record concurrently
    num_files = 3
    success_results = []
    
    with ThreadPoolExecutor(max_workers=num_files) as executor:
        futures = [
            executor.submit(add_file_to_record, i) 
            for i in range(num_files)
        ]
        
        for future in as_completed(futures, timeout=25):
            try:
                success = future.result()
                success_results.append(success)
            except Exception as e:
                pytest.fail(f"Record thread safety test failed: {e}")

    # Verify all operations succeeded
    assert all(success_results), f"Some operations failed: {success_results}"
    
    # Verify final record state BEFORE app shutdown
    # Files with trailing digits get normalized (usr-ipat-threadsafe0 -> usr-ipat-threadsafe)
    # And usr-ipat maps to IPAT/USR directory structure
    expected_dir = tmp_settings.DEST_DIR / "IPAT" / "USR" / "threadsafe"
    assert expected_dir.exists(), f"Expected directory {expected_dir} not created"
    
    processed_files = [f for f in expected_dir.iterdir() if f.suffix == '.tif']
    assert len(processed_files) == num_files, \
        f"Expected {num_files} files, found {len(processed_files)}: {processed_files}"
    
    # Verify record manager state is consistent (check before app shutdown)
    from ipat_watchdog.core.config.settings_store import SettingsStore
    from ipat_watchdog.core.storage.filesystem_utils import generate_record_id
    
    settings = SettingsStore.get()
    sanitized_prefix = f"usr{settings.ID_SEP}ipat{settings.ID_SEP}threadsafe"
    # Use hardcoded TischREM record ID for this test
    record_id = f"rem_01{settings.ID_SEP}{sanitized_prefix}".lower()
    
    record_manager = concurrent_test_app.file_processing.records
    record = record_manager.get_record_by_id(record_id)
    
    assert record is not None, f"Record {record_id} not found in record manager"
    assert len(record.files_uploaded) == num_files, \
        f"Record shows {len(record.files_uploaded)} files, expected {num_files}"