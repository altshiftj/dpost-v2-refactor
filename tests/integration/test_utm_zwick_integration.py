from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ipat_watchdog.core.processing.file_process_manager import FileProcessManager
from ipat_watchdog.core.storage.filesystem_utils import get_record_path, init_dirs
from ipat_watchdog.device_plugins.utm_zwick.settings import build_config as build_utm_config
from ipat_watchdog.pc_plugins.test_pc.settings import build_config as build_pc_config
from tests.helpers.fake_sync import DummySyncManager
from tests.helpers.fake_ui import HeadlessUI
from tests.helpers.fake_session import FakeSessionManager
from ipat_watchdog.core.config import init_config, reset_service


@pytest.fixture
def utm_processing_manager(tmp_path):
    root = tmp_path / "sandbox"
    overrides = {
        "app_dir": root / "App",
        "watch_dir": root / "Upload",
        "dest_dir": root / "Data",
        "rename_dir": root / "Data" / "00_To_Rename",
        "exceptions_dir": root / "Data" / "01_Exceptions",
        "daily_records_json": root / "records.json",
    }

    pc_config = build_pc_config(override_paths=overrides)
    utm_config = build_utm_config()
    utm_config = replace(
        utm_config,
        watcher=replace(utm_config.watcher, poll_seconds=0.05, stable_cycles=1, max_wait_seconds=5.0),
    )

    service = init_config(pc_config, [utm_config])
    init_dirs()

    ui = HeadlessUI()
    sync = DummySyncManager(ui)
    session = FakeSessionManager(interactions=ui, scheduler=ui)
    fpm = FileProcessManager(
        interactions=ui,
        sync_manager=sync,
        session_manager=session,
        config_service=service,
    )
    try:
        yield fpm, ui
    finally:
        reset_service()


def _process_pair(fpm, ui, watch_dir: Path, prefix: str, first: str, second: str) -> Path:
    first_path = watch_dir / f"{prefix}.{first}"
    second_path = watch_dir / f"{prefix}.{second}"
    first_path.write_text("raw-binary")
    second_path.write_text("excel-sheet")

    fpm.process_item(str(first_path))
    fpm.process_item(str(second_path))

    return Path(get_record_path(prefix, "UTM"))


def test_end_to_end_pair_processing_utm_zwick(utm_processing_manager, tmp_settings):
    fpm, ui = utm_processing_manager
    prefix = "usr-ipat-tensileA"

    record_dir = _process_pair(fpm, ui, tmp_settings.WATCH_DIR, prefix, "zs2", "xlsx")

    zip_path = record_dir / "UTM-tensileA.zs2.zip"
    moved_xlsx = record_dir / "UTM-tensileA-01.xlsx"

    assert zip_path.exists(), "Zipped .zs2 not found"
    assert moved_xlsx.exists(), "Moved .xlsx not found"


def test_end_to_end_pair_processing_reverse_order(utm_processing_manager, tmp_settings):
    fpm, ui = utm_processing_manager
    prefix = "usr-ipat-tensileB"

    record_dir = _process_pair(fpm, ui, tmp_settings.WATCH_DIR, prefix, "xlsx", "zs2")

    zip_path = record_dir / "UTM-tensileB.zs2.zip"
    moved_xlsx = record_dir / "UTM-tensileB-01.xlsx"

    assert zip_path.exists(), "Zipped .zs2 not found (reverse order)"
    assert moved_xlsx.exists(), "Moved .xlsx not found (reverse order)"
