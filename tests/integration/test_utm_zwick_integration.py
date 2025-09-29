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


def _emit_and_process(fpm, watch_dir: Path, prefix: str, order: list[str]) -> Path:
    """
    order items can be:
      - "zs2"        -> {prefix}.zs2
      - "csv"        -> {prefix}.csv
      - "txt-<NN>"   -> {prefix}-<NN>.txt (e.g., "txt-01", "txt-02")

    Returns the record directory path.
    """
    for token in order:
        if token == "zs2":
            p = watch_dir / f"{prefix}.zs2"
            p.write_text("raw-zs2")
        elif token == "csv":
            p = watch_dir / f"{prefix}.csv"
            p.write_text("final-results")
        elif token.startswith("txt-"):
            nn = token.split("-", 1)[1]
            p = watch_dir / f"{prefix}-{nn}.txt"
            p.write_text(f"snapshot-{nn}")
        else:
            raise ValueError(f"Unknown token in order: {token}")
        fpm.process_item(str(p))

    return Path(get_record_path(prefix, "UTM"))


def _expect_exists(record_dir: Path, *names: str) -> None:
    for name in names:
        path = record_dir / name
        assert path.exists(), f"Expected file not found: {path}"


def test_end_to_end_series_processing_with_txt_and_csv(utm_processing_manager, tmp_settings):
    fpm, ui = utm_processing_manager
    prefix = "usr-ipat-tensileA"

    # zs2 and txt snapshots arrive before csv (finalizes on csv)
    record_dir = _emit_and_process(
        fpm,
        tmp_settings.WATCH_DIR,
        prefix,
        order=["zs2", "txt-01", "txt-02", "csv"],
    )

    # Expected names now overwrite deterministically without numeric counters
    _expect_exists(
        record_dir,
        "UTM-tensileA_raw.zs2",
        "UTM-tensileA_results.csv",
    )

    # Check that at least two *_tests*.txt exist
    tests = list(record_dir.glob("UTM-tensileA_tests-*.txt"))
    assert len(tests) >= 2, f"Expected >= 2 text snapshots, found: {len(tests)}"
