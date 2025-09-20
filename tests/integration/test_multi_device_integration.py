from __future__ import annotations

import time
import os
from pathlib import Path

import pytest
from watchdog.observers.polling import PollingObserver

from ipat_watchdog.core.app.device_watchdog_app import DeviceWatchdogApp
from ipat_watchdog.core.processing.file_process_manager import FileProcessManager
from ipat_watchdog.core.processing.models import ProcessingStatus
from ipat_watchdog.core.storage.filesystem_utils import init_dirs
from tests.helpers.fake_sync import DummySyncManager
from tests.helpers.fake_ui import HeadlessUI


# ────────────────────────── fixtures ──────────────────────────────────────────
@pytest.fixture
def multi_device_app(tmp_settings):
    """
    Build DeviceWatchdogApp using the standard test device setup.
    Tests basic file processing scenarios that would apply to multi-device environments.
    """

    ui = HeadlessUI()
    sync = DummySyncManager(ui)

    # Use the same setup as the main integration tests
    from ipat_watchdog.core.config.settings_store import SettingsStore, SettingsManager
    from ipat_watchdog.pc_plugins.test_pc.settings import TestPCSettings
    from ipat_watchdog.device_plugins.test_device.settings import TestDeviceSettings

    # Create PC and device settings with test paths
    pc_settings = TestPCSettings()
    pc_settings.APP_DIR = tmp_settings.APP_DIR
    pc_settings.WATCH_DIR = tmp_settings.WATCH_DIR
    pc_settings.DEST_DIR = tmp_settings.DEST_DIR
    pc_settings.RENAME_DIR = tmp_settings.RENAME_DIR
    pc_settings.EXCEPTIONS_DIR = tmp_settings.EXCEPTIONS_DIR
    pc_settings.DAILY_RECORDS_JSON = tmp_settings.DAILY_RECORDS_JSON
    pc_settings.LOG_FILE = tmp_settings.LOG_FILE

    device_settings = TestDeviceSettings()
    device_settings.APP_DIR = tmp_settings.APP_DIR
    device_settings.WATCH_DIR = tmp_settings.WATCH_DIR
    device_settings.DEST_DIR = tmp_settings.DEST_DIR
    device_settings.RENAME_DIR = tmp_settings.RENAME_DIR
    device_settings.EXCEPTIONS_DIR = tmp_settings.EXCEPTIONS_DIR
    device_settings.DAILY_RECORDS_JSON = tmp_settings.DAILY_RECORDS_JSON
    device_settings.LOG_FILE = tmp_settings.LOG_FILE
    
    # Register the test device
    settings_manager = SettingsManager([device_settings], pc_settings)
    SettingsStore.set_manager(settings_manager)

    # Create directories using the proper settings
    init_dirs()

    app = DeviceWatchdogApp(
        ui=ui,
        sync_manager=sync,
        settings_manager=settings_manager,
        file_process_manager_cls=FileProcessManager,
    )

    app.initialize()
    yield app
    app.on_closing()


# ───────────────────────── Multi-Device Integration Tests ─────────────────────────────────
def wait_until(predicate, timeout=5.0, interval=0.05):
    """Wait until predicate() returns True or timeout expires."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False

def run_scheduled_tasks(ui: HeadlessUI, max_steps: int = 50):
    """Execute scheduled UI callbacks to simulate the main-loop timer."""
    steps = 0
    while steps < max_steps and ui.scheduled_tasks:
        tasks = list(ui.scheduled_tasks)
        ui.scheduled_tasks.clear()
        for _, cb in tasks:
            cb()
        steps += 1

def test_basic_file_processing_works(multi_device_app, tmp_settings):
    """Test that basic file processing works with test device."""
    prefix = "mus-ipat-sample"
    tif_path = tmp_settings.WATCH_DIR / f"{prefix}.tif"
    tif_path.write_bytes(b"dummy test image")

    # Process the file directly
    multi_device_app.file_processing.process_item(str(tif_path))
    # Drive stability tracker probes
    
    # Test device uses DEVICE_ABBR in folder structure: INSTITUTE/USER/TEST-SAMPLE
    expected_dir = tmp_settings.DEST_DIR / "IPAT" / "MUS" / "TEST-sample"
    assert expected_dir.exists(), f"Expected directory {expected_dir} does not exist"
    
    # Test device copies files with original names
    tif_files = [f for f in expected_dir.iterdir() if f.suffix == '.tif']
    assert len(tif_files) == 1, f"Expected exactly 1 processed file, found {len(tif_files)}: {tif_files}"
    
    # Verify original file was moved
    assert not tif_path.exists(), f"Original file should be moved: {tif_path}"

def test_text_file_processing_works(multi_device_app, tmp_settings):
    """Test that .txt files are also processed by test device."""
    prefix = "mus-ipat-sample"
    
    # Test device handles .txt files too
    txt_path = tmp_settings.WATCH_DIR / f"{prefix}.txt"
    txt_path.write_bytes(b"dummy test data")
    # Process the file directly
    multi_device_app.file_processing.process_item(str(txt_path))

    # Test device uses DEVICE_ABBR in folder structure: INSTITUTE/USER/TEST-SAMPLE
    expected_dir = tmp_settings.DEST_DIR / "IPAT" / "MUS" / "TEST-sample"
    assert expected_dir.exists(), f"Expected directory {expected_dir} does not exist"
    # Test device copies files with original names
    txt_files = [f for f in expected_dir.iterdir() if f.suffix == '.txt']
    assert len(txt_files) == 1, f"Expected exactly 1 processed .txt file, found {len(txt_files)}: {txt_files}"
    # Verify original file was moved
    assert not txt_path.exists(), f"Original file should be moved: {txt_path}"


def test_unsupported_file_rejected(multi_device_app, tmp_settings):
    """Test that files not supported by test device are moved to exceptions."""
    unsupported_path = tmp_settings.WATCH_DIR / "mus-ipat-sample.pdf"
    unsupported_path.write_bytes(b"unsupported file type")

    result = multi_device_app.file_processing.process_item(str(unsupported_path))
    assert result.status is ProcessingStatus.REJECTED

    # Check exceptions directory for the file
    exception_files = list(tmp_settings.EXCEPTIONS_DIR.glob("mus-ipat-sample*.pdf"))
    assert len(exception_files) == 1
    assert exception_files[0].exists()

def test_multiple_files_same_record(multi_device_app, tmp_settings):
    """Test that multiple files with the same base name get processed correctly."""
    base_name = "mus-ipat-sample"
    
    # Create 3 files with same name to test processing
    for i in range(3):
        # Create in temporary subdirectories to avoid filesystem conflicts during test setup
        temp_dir = tmp_settings.WATCH_DIR / f"temp{i}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        file_path = temp_dir / f"{base_name}.tif"
        file_path.write_bytes(f"dummy test image data {i}".encode())
        # Process each file
        multi_device_app.file_processing.process_item(str(file_path))

    # Verify all files were processed and placed correctly
    # Test device uses DEVICE_ABBR: INSTITUTE/USER/TEST-SAMPLE
    base_dir = tmp_settings.DEST_DIR / "IPAT" / "MUS"
    assert base_dir.exists(), f"Base directory {base_dir} was not created"
    
    # Check that files were processed - may be in sample, sample_0, sample_1 etc. due to collisions
    processed_files = []
    for subdir in base_dir.iterdir():
        if subdir.is_dir() and (subdir.name == 'TEST-sample' or subdir.name.startswith('TEST-sample_')):
            for f in subdir.iterdir():
                if f.suffix == '.tif':
                    processed_files.append(f)
    
    assert len(processed_files) == 3, f"Expected 3 processed files, found {len(processed_files)}: {processed_files}"


def test_different_user_groups_no_collision(multi_device_app, tmp_settings):
    """Test that files for different user/institute groups don't interfere."""
    test_files = [
        ("mus-ipat-sample1", "mus", "ipat"),
        ("abc-xyz-sample2", "abc", "xyz"),
        ("def-uvw-sample3", "def", "uvw"),
    ]
    
    expected_dirs = []
    
    # Process files sequentially
    for filename, user, institute in test_files:
        file_path = tmp_settings.WATCH_DIR / f"{filename}.tif"
        file_path.write_bytes(f"data for {filename}".encode())
        multi_device_app.file_processing.process_item(str(file_path))
        # Calculate expected directory (test device doesn't normalize trailing digits)
        expected_dir = tmp_settings.DEST_DIR / institute.upper() / user.upper() / f"TEST-{filename.split('-')[2]}"
        expected_dirs.append(expected_dir)

    # Verify each file group created its own directory structure
    for expected_dir in expected_dirs:
        assert expected_dir.exists(), f"Expected directory {expected_dir} was not created"
        tif_files = [f for f in expected_dir.iterdir() if f.suffix == '.tif']
        assert len(tif_files) == 1, f"Expected 1 file in {expected_dir}, found {len(tif_files)}: {tif_files}"


def test_mixed_file_types_processed_correctly(multi_device_app, tmp_settings):
    """Test that different file types are all processed by the test device."""
    # Create files for both supported types
    tif_path = tmp_settings.WATCH_DIR / "mus-ipat-image.tif"
    txt_path = tmp_settings.WATCH_DIR / "mus-ipat-data.txt"
    
    tif_path.write_bytes(b"Test image")
    txt_path.write_bytes(b"Test data")

    # Process files directly
    multi_device_app.file_processing.process_item(str(tif_path))
    multi_device_app.file_processing.process_item(str(txt_path))

    # Verify both files were processed
    expected_base = tmp_settings.DEST_DIR / "IPAT" / "MUS"
    
    # Check image file 
    image_dir = expected_base / "TEST-image"
    assert image_dir.exists(), f"Image directory {image_dir} not found"
    image_files = [f for f in image_dir.iterdir() if f.suffix == '.tif']
    assert len(image_files) == 1, f"Expected 1 image file, found {len(image_files)}: {image_files}"
    
    # Check data file
    data_dir = expected_base / "TEST-data"
    assert data_dir.exists(), f"Data directory {data_dir} not found"
    data_files = [f for f in data_dir.iterdir() if f.suffix == '.txt']
    assert len(data_files) == 1, f"Expected 1 data file, found {len(data_files)}: {data_files}"
    
    # Verify originals were processed
    assert not tif_path.exists(), "Image file should be moved"
    assert not txt_path.exists(), "Data file should be moved"
