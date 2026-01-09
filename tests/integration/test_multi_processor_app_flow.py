from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

import ipat_watchdog.plugin_system as plugin_system
from ipat_watchdog.core.app.device_watchdog_app import DeviceWatchdogApp
from ipat_watchdog.core.config import init_config, reset_service
from ipat_watchdog.core.processing.file_process_manager import FileProcessManager
from ipat_watchdog.core.processing.stability_tracker import (
    FileStabilityTracker,
    StabilityOutcome,
)
from ipat_watchdog.core.storage.filesystem_utils import init_dirs
from ipat_watchdog.device_plugins.rmx_eirich_el1.settings import (
    build_config as build_eirich_el1_config,
)
from ipat_watchdog.device_plugins.rmx_eirich_r01.settings import (
    build_config as build_eirich_r01_config,
)
from ipat_watchdog.device_plugins.utm_zwick.settings import (
    build_config as build_utm_config,
)
from ipat_watchdog.pc_plugins.test_pc.settings import build_config as build_pc_config
from ipat_watchdog.plugin_system import PluginLoader
from tests.helpers.fake_observer import FakeObserver
from tests.helpers.fake_sync import DummySyncManager
from tests.helpers.fake_ui import HeadlessUI
from tests.helpers.task_runner import drain_scheduled_tasks

EIRICH_CASES = (
    {
        "filename": "Eirich_EL1_TrendFile_20250924_095653.txt",
        "sample_id": "eirich_el1",
        "device_abbr": "RMX_01",
    },
    {
        "filename": "Eirich_R01_TrendFile_20250731_103330.txt",
        "sample_id": "eirich_r01",
        "device_abbr": "RMX_02",
    },
)

DEVICE_PLUGIN_SPECS = (
    {
        "name": "test-eirich-el1",
        "module": "ipat_watchdog.device_plugins.rmx_eirich_el1.plugin",
        "config_builder": build_eirich_el1_config,
    },
    {
        "name": "test-eirich-r01",
        "module": "ipat_watchdog.device_plugins.rmx_eirich_r01.plugin",
        "config_builder": build_eirich_r01_config,
    },
    {
        "name": "test-utm-zwick",
        "module": "ipat_watchdog.device_plugins.utm_zwick.plugin",
        "config_builder": build_utm_config,
    },
)


def _build_path_overrides(tmp_path: Path) -> tuple[dict[str, Path], SimpleNamespace]:
    root = tmp_path / "sandbox"
    overrides = {
        "app_dir": root / "App",
        "watch_dir": root / "Upload",
        "dest_dir": root / "Data",
        "rename_dir": root / "Data" / "00_To_Rename",
        "exceptions_dir": root / "Data" / "01_Exceptions",
        "daily_records_json": root / "records.json",
    }
    paths = SimpleNamespace(
        APP_DIR=overrides["app_dir"],
        WATCH_DIR=overrides["watch_dir"],
        DEST_DIR=overrides["dest_dir"],
        RENAME_DIR=overrides["rename_dir"],
        EXCEPTIONS_DIR=overrides["exceptions_dir"],
        DAILY_RECORDS_JSON=overrides["daily_records_json"],
    )
    return overrides, paths


@pytest.fixture
def multi_processor_app(tmp_path, monkeypatch):
    overrides, paths = _build_path_overrides(tmp_path)
    pc_config = build_pc_config(override_paths=overrides)
    device_configs = [spec["config_builder"]() for spec in DEVICE_PLUGIN_SPECS]
    config_service = init_config(pc_config, device_configs)
    init_dirs()

    loader = PluginLoader(load_entrypoints=False, load_builtins=False)
    for spec in DEVICE_PLUGIN_SPECS:
        module = importlib.import_module(spec["module"])
        loader.register_plugin(module, name=spec["name"])
    monkeypatch.setattr(plugin_system, "_PLUGIN_LOADER_SINGLETON", loader)

    monkeypatch.setattr(
        FileStabilityTracker,
        "wait",
        lambda self: StabilityOutcome(path=self.file_path, stable=True),
    )

    ui = HeadlessUI()
    sync = DummySyncManager(ui)
    observer_stub = FakeObserver()
    monkeypatch.setattr(
        "ipat_watchdog.core.app.device_watchdog_app.Observer",
        lambda: observer_stub,
    )

    app = DeviceWatchdogApp(
        ui=cast(Any, ui),
        sync_manager=sync,
        config_service=config_service,
        file_process_manager_cls=FileProcessManager,
    )
    app.initialize()
    try:
        yield app, ui, sync, paths
    finally:
        app.on_closing()
        reset_service()


def test_multi_processor_app_flow(multi_processor_app):
    app, ui, sync, paths = multi_processor_app
    ui.rename_inputs = [
        {"name": "mus", "institute": "ipat", "sample_ID": case["sample_id"]}
        for case in EIRICH_CASES
    ]

    watch_dir = paths.WATCH_DIR
    watch_dir.mkdir(parents=True, exist_ok=True)

    eirich_paths = []
    for case in EIRICH_CASES:
        path = watch_dir / case["filename"]
        path.write_text(f"{case['sample_id']} payload", encoding="utf-8")
        eirich_paths.append(path)

    prefix = "usr-ipat-tensileA"
    zs2_path = watch_dir / f"{prefix}.zs2"
    txt1_path = watch_dir / f"{prefix}-01.txt"
    txt2_path = watch_dir / f"{prefix}-02.txt"
    csv_path = watch_dir / f"{prefix}.csv"
    zs2_path.write_text("zs2 payload", encoding="utf-8")
    txt1_path.write_text("snapshot 1", encoding="utf-8")
    txt2_path.write_text("snapshot 2", encoding="utf-8")
    csv_path.write_text("results", encoding="utf-8")

    # Seed the UTM series without scheduling deferred retries through the app queue.
    for path in (zs2_path, txt1_path, txt2_path):
        app.file_processing.process_item(str(path))

    for path in (*eirich_paths, csv_path):
        app.event_queue.put(str(path))

    drain_scheduled_tasks(ui)

    for case in EIRICH_CASES:
        record_dir = paths.DEST_DIR / "IPAT" / "MUS" / f"{case['device_abbr']}-{case['sample_id']}"
        assert record_dir.exists()
        assert len(list(record_dir.glob("*.txt"))) == 1

    utm_dir = paths.DEST_DIR / "IPAT" / "USR" / "UTM-tensileA"
    assert utm_dir.exists()
    assert list(utm_dir.glob("UTM-tensileA-*.zs2"))
    assert list(utm_dir.glob("UTM-tensileA_results-*.csv"))
    txt_snapshots = list(utm_dir.glob("UTM-tensileA_tests*.txt"))
    assert len(txt_snapshots) >= 2

    for path in (*eirich_paths, zs2_path, txt1_path, txt2_path, csv_path):
        assert not path.exists()

    assert len(ui.calls["show_rename_dialog"]) == 2
    assert not ui.errors
    assert sync.synced_records


def test_eirich_invalid_filename_moves_to_rename_folder(multi_processor_app):
    app, ui, _, paths = multi_processor_app
    ui.rename_inputs = []

    watch_dir = paths.WATCH_DIR
    watch_dir.mkdir(parents=True, exist_ok=True)

    target = watch_dir / "Eirich_EL1_TrendFile_20250924_095653.txt"
    target.write_text("payload", encoding="utf-8")

    app.event_queue.put(str(target))
    drain_scheduled_tasks(ui)

    assert not target.exists()
    rename_hits = list(paths.RENAME_DIR.glob("Eirich_EL1_TrendFile_*.txt"))
    assert rename_hits
    assert ui.calls["show_rename_dialog"]
