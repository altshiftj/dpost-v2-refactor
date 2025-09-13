from __future__ import annotations

import time
from pathlib import Path

import pytest

from ipat_watchdog.core.processing.file_process_manager import FileProcessManager
from ipat_watchdog.core.config.settings_store import SettingsStore, SettingsManager
from ipat_watchdog.device_plugins.utm_zwick.settings import SettingsZwickUTM
from tests.helpers.fake_ui import HeadlessUI
from tests.helpers.fake_sync import DummySyncManager
from tests.helpers.fake_session import FakeSessionManager
from ipat_watchdog.pc_plugins.test_pc.plugin import TestPCPlugin
from ipat_watchdog.core.storage.filesystem_utils import get_record_path


@pytest.fixture
def utm_processing_manager(tmp_settings):
    """FileProcessManager configured for UTM Zwick with fast stability."""
    # Reuse tmp_settings' sandbox paths for isolation
    path_overrides = {
        attr: getattr(tmp_settings, attr)
        for attr in [
            "APP_DIR",
            "WATCH_DIR",
            "DEST_DIR",
            "RENAME_DIR",
            "EXCEPTIONS_DIR",
            "DAILY_RECORDS_JSON",
        ]
        if hasattr(tmp_settings, attr)
    }

    utm = SettingsZwickUTM()
    # Apply same directory layout to UTM settings
    for k, v in path_overrides.items():
        setattr(utm, k, v)

    # Speed up stability checks for tests
    utm.POLL_SECONDS = 0.05
    utm.STABLE_CYCLES = 1
    utm.MAX_WAIT_SECONDS = 5.0

    # Build PC settings with overrides so FileProcessManager has concrete PCSettings
    pc_plugin = TestPCPlugin(override_paths=path_overrides)
    pc_settings = pc_plugin.get_settings()

    # Build a SettingsManager with UTM device only and test PC settings
    sm = SettingsManager(available_devices=[utm], pc_settings=pc_settings)
    SettingsStore.set_manager(sm)

    ui = HeadlessUI()
    sync = DummySyncManager(ui=ui)
    fpm = FileProcessManager(
        ui=ui,
        sync_manager=sync,
        session_manager=FakeSessionManager(ui=ui),
        settings_manager=sm,
    )
    return fpm, utm


def _wait_until(predicate, timeout=3.0, interval=0.05):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def test_end_to_end_pair_processing_utm_zwick(utm_processing_manager, tmp_settings):
    fpm, utm = utm_processing_manager

    # Valid prefix to avoid rename flow
    prefix = "usr-ipat-tensileA"
    zs2 = tmp_settings.WATCH_DIR / f"{prefix}.zs2"
    xlsx = tmp_settings.WATCH_DIR / f"{prefix}.xlsx"
    zs2.write_text("raw-binary")
    xlsx.write_text("excel-sheet")

    # Process first arrival → staged only
    fpm.process_item(str(zs2))
    # Process second arrival → triggers processing of the pair
    fpm.process_item(str(xlsx))

    # Expected record directory and files (use helper to mirror production path)
    record_dir = Path(get_record_path(prefix, "UTM"))
    zip_path = record_dir / "UTM-tensileA.zs2.zip"
    moved_xlsx = record_dir / "UTM-tensileA-01.xlsx"

    # Wait for stability service to complete asynchronous processing
    assert _wait_until(lambda: record_dir.exists()), "Record directory not created in time"
    assert _wait_until(lambda: zip_path.exists()), "Zipped .zs2 not found in time"
    assert _wait_until(lambda: moved_xlsx.exists()), "Moved .xlsx not found in time"

    # Source files should be gone from watch dir (.zs2 deleted, .xlsx moved)
    assert not zs2.exists(), "Raw .zs2 should be removed after archiving"
    assert not xlsx.exists(), "Original .xlsx should be moved to record directory"


def test_end_to_end_pair_processing_reverse_order(utm_processing_manager, tmp_settings):
    fpm, utm = utm_processing_manager

    prefix = "usr-ipat-tensileB"
    zs2 = tmp_settings.WATCH_DIR / f"{prefix}.zs2"
    xlsx = tmp_settings.WATCH_DIR / f"{prefix}.xlsx"
    zs2.write_text("raw-binary")
    xlsx.write_text("excel-sheet")

    # Reverse arrival: .xlsx first, then .zs2
    fpm.process_item(str(xlsx))
    fpm.process_item(str(zs2))

    record_dir = Path(get_record_path(prefix, "UTM"))
    zip_path = record_dir / "UTM-tensileB.zs2.zip"
    moved_xlsx = record_dir / "UTM-tensileB-01.xlsx"

    assert _wait_until(lambda: zip_path.exists()), "Zipped .zs2 not found in time (reverse order)"
    assert _wait_until(lambda: moved_xlsx.exists()), "Moved .xlsx not found in time (reverse order)"
