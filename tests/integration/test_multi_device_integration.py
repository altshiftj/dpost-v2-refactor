from __future__ import annotations

from pathlib import Path

import pytest

from ipat_watchdog.core.processing.file_process_manager import FileProcessManager
from ipat_watchdog.core.processing.models import ProcessingStatus
from ipat_watchdog.core.storage.filesystem_utils import init_dirs
from tests.helpers.fake_sync import DummySyncManager
from tests.helpers.fake_ui import HeadlessUI
from tests.helpers.fake_session import FakeSessionManager


def run_scheduled_tasks(ui: HeadlessUI, max_steps: int = 50) -> None:
    steps = 0
    while steps < max_steps and ui.scheduled_tasks:
        tasks = list(ui.scheduled_tasks)
        ui.scheduled_tasks.clear()
        for _, cb in tasks:
            cb()
        steps += 1


@pytest.fixture
def processing_components(config_service):
    """Return a tuple of (FileProcessManager, HeadlessUI) wired to the test config."""
    init_dirs()
    ui = HeadlessUI()
    sync = DummySyncManager(ui)
    session = FakeSessionManager(interactions=ui, scheduler=ui)
    manager = FileProcessManager(
        interactions=ui,
        sync_manager=sync,
        session_manager=session,
        config_service=config_service,
    )
    return manager, ui


# ---------------------------------------------------------------------------
# Multi-device style scenarios (using the test device config)
# ---------------------------------------------------------------------------


def test_basic_file_processing_works(processing_components, tmp_settings):
    fpm, ui = processing_components
    prefix = "mus-ipat-sample"
    tif_path = tmp_settings.WATCH_DIR / f"{prefix}.tif"
    tif_path.write_bytes(b"dummy test image")

    fpm.process_item(str(tif_path))
    run_scheduled_tasks(ui)

    expected_dir = tmp_settings.DEST_DIR / "IPAT" / "MUS" / "TEST-sample"
    assert expected_dir.exists(), f"Expected directory {expected_dir} does not exist"

    tif_files = [f for f in expected_dir.iterdir() if f.suffix == ".tif"]
    assert len(tif_files) == 1, f"Expected exactly 1 processed file, found {len(tif_files)}: {tif_files}"
    assert not tif_path.exists(), f"Original file should be moved: {tif_path}"


def test_text_file_processing_works(processing_components, tmp_settings):
    fpm, ui = processing_components
    prefix = "mus-ipat-sample"
    txt_path = tmp_settings.WATCH_DIR / f"{prefix}.txt"
    txt_path.write_bytes(b"dummy test data")

    fpm.process_item(str(txt_path))
    run_scheduled_tasks(ui)

    expected_dir = tmp_settings.DEST_DIR / "IPAT" / "MUS" / "TEST-sample"
    assert expected_dir.exists()
    txt_files = [f for f in expected_dir.iterdir() if f.suffix == ".txt"]
    assert len(txt_files) == 1, f"Expected 1 processed txt file, found {len(txt_files)}"
    assert not txt_path.exists()


def test_unsupported_file_rejected(processing_components, tmp_settings):
    fpm, ui = processing_components
    unsupported_path = tmp_settings.WATCH_DIR / "mus-ipat-sample.pdf"
    unsupported_path.write_bytes(b"unsupported file type")

    result = fpm.process_item(str(unsupported_path))
    assert result.status is ProcessingStatus.REJECTED

    exception_files = list(tmp_settings.EXCEPTIONS_DIR.glob("mus-ipat-sample*.pdf"))
    assert len(exception_files) == 1
    assert exception_files[0].exists()


def test_multiple_files_same_record(processing_components, tmp_settings):
    fpm, ui = processing_components
    base_name = "mus-ipat-sample"

    for i in range(3):
        file_path = tmp_settings.WATCH_DIR / f"{base_name}.tif"
        file_path.write_bytes(f"dummy test image data {i}".encode())
        fpm.process_item(str(file_path))
        run_scheduled_tasks(ui)

    base_dir = tmp_settings.DEST_DIR / "IPAT" / "MUS"
    assert base_dir.exists()

    processed_files = []
    for subdir in base_dir.iterdir():
        if subdir.is_dir() and subdir.name.startswith("TEST-sample"):
            processed_files.extend(f for f in subdir.iterdir() if f.suffix == ".tif")

    assert len(processed_files) == 3, f"Expected 3 processed files, found {len(processed_files)}"


def test_different_user_groups_no_collision(processing_components, tmp_settings):
    fpm, ui = processing_components
    test_files = [
        ("mus-ipat-sample1", "mus", "ipat"),
        ("abc-xyz-sample2", "abc", "xyz"),
        ("def-uvw-sample3", "def", "uvw"),
    ]

    expected_dirs = []
    for filename, user, institute in test_files:
        file_path = tmp_settings.WATCH_DIR / f"{filename}.tif"
        file_path.write_bytes(f"data for {filename}".encode())
        fpm.process_item(str(file_path))
        run_scheduled_tasks(ui)
        expected_dirs.append(tmp_settings.DEST_DIR / institute.upper() / user.upper() / f"TEST-{filename.split('-')[2]}")

    for expected_dir in expected_dirs:
        assert expected_dir.exists(), f"Expected directory {expected_dir} was not created"
        tif_files = [f for f in expected_dir.iterdir() if f.suffix == ".tif"]
        assert len(tif_files) == 1


def test_mixed_file_types_processed_correctly(processing_components, tmp_settings):
    fpm, ui = processing_components
    tif_path = tmp_settings.WATCH_DIR / "mus-ipat-image.tif"
    txt_path = tmp_settings.WATCH_DIR / "mus-ipat-data.txt"
    tif_path.write_bytes(b"Test image")
    txt_path.write_bytes(b"Test data")

    fpm.process_item(str(tif_path))
    fpm.process_item(str(txt_path))
    run_scheduled_tasks(ui)

    expected_base = tmp_settings.DEST_DIR / "IPAT" / "MUS"
    image_dir = expected_base / "TEST-image"
    data_dir = expected_base / "TEST-data"

    assert image_dir.exists(), f"Image directory {image_dir} not found"
    assert data_dir.exists(), f"Data directory {data_dir} not found"

    image_files = [f for f in image_dir.iterdir() if f.suffix == ".tif"]
    data_files = [f for f in data_dir.iterdir() if f.suffix == ".txt"]

    assert len(image_files) == 1
    assert len(data_files) == 1
    assert not tif_path.exists()
    assert not txt_path.exists()
