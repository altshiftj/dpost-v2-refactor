from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from ipat_watchdog.core.config import init_config, reset_service
from ipat_watchdog.core.processing.file_process_manager import FileProcessManager
from ipat_watchdog.core.processing.stability_tracker import FileStabilityTracker, StabilityOutcome
from ipat_watchdog.core.storage.filesystem_utils import (
    generate_file_id,
    get_record_path,
    get_unique_filename,
    init_dirs,
)
from ipat_watchdog.device_plugins.erm_hioki.file_processor import FileProcessorHioki
from ipat_watchdog.device_plugins.erm_hioki.settings import build_config as build_hioki_config
from ipat_watchdog.pc_plugins.test_pc.settings import build_config as build_pc_config
from tests.helpers.fake_session import FakeSessionManager
from tests.helpers.fake_sync import DummySyncManager
from tests.helpers.fake_ui import HeadlessUI


@pytest.fixture
def hioki_manager(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "sandbox"
    watch_dir = root / "Upload"
    dest_dir = root / "Data"
    overrides = {
        "app_dir": root / "App",
        "watch_dir": watch_dir,
        "dest_dir": dest_dir,
        "rename_dir": dest_dir / "00_To_Rename",
        "exceptions_dir": dest_dir / "01_Exceptions",
        "daily_records_json": root / "records.json",
    }

    pc_config = build_pc_config(override_paths=overrides)
    device_config = build_hioki_config()
    device_config = replace(
        device_config,
        watcher=replace(
            device_config.watcher,
            poll_seconds=0.0,
            max_wait_seconds=1.0,
            stable_cycles=1,
        ),
    )

    service = init_config(pc_config, [device_config])
    init_dirs()

    monkeypatch.setattr(
        FileStabilityTracker,
        "wait",
        lambda self: StabilityOutcome(path=self.file_path, stable=True),
    )

    ui = HeadlessUI()
    sync = DummySyncManager(ui)
    session = FakeSessionManager(interactions=ui, scheduler=ui)
    manager = FileProcessManager(
        interactions=ui,
        sync_manager=sync,
        session_manager=session,
        config_service=service,
        file_processor=FileProcessorHioki(device_config),
    )

    yield manager, device_config, SimpleNamespace(WATCH_DIR=watch_dir, DEST_DIR=dest_dir)
    reset_service()


def test_measurement_processed_even_when_aggregate_exists(hioki_manager):
    manager, device_config, paths = hioki_manager
    prefix = "jfi-ipat-hioki_test"

    measurement = paths.WATCH_DIR / f"{prefix}_20260114183851.csv"
    measurement.write_text("measurement")
    aggregate = paths.WATCH_DIR / f"{prefix}.csv"
    aggregate.write_text("agg-data")
    cc_file = paths.WATCH_DIR / f"CC_{prefix}.csv"
    cc_file.write_text("cc-data")

    manager.process_item(str(measurement))

    device_abbr = device_config.metadata.device_abbr
    record_path = get_record_path(prefix, device_abbr)
    file_id = generate_file_id(prefix, device_abbr)
    expected_measurement = get_unique_filename(record_path, file_id, ".csv")

    assert Path(expected_measurement).exists()
    assert not measurement.exists()
