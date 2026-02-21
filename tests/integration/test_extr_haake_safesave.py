"""Integration test for EXTR HAAKE plugin handling Excel safe-save (disappear/reappear)."""
from __future__ import annotations

import importlib
import threading
import time
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest

from dpost.application.runtime.device_watchdog_app import DeviceWatchdogApp
from ipat_watchdog.core.config import init_config, reset_service
from ipat_watchdog.core.processing.file_process_manager import FileProcessManager
from ipat_watchdog.core.storage.filesystem_utils import init_dirs
from ipat_watchdog.device_plugins.extr_haake.settings import build_config as build_extr_haake_config
from ipat_watchdog.pc_plugins.test_pc.settings import build_config as build_pc_config
from tests.helpers.fake_observer import FakeObserver
from tests.helpers.fake_sync import DummySyncManager
from tests.helpers.fake_ui import HeadlessUI
from tests.helpers.task_runner import drain_scheduled_tasks


@pytest.fixture
def app_with_extr_haake(tmp_path):
    """Real pipeline app configured with extr_haake device in a sandbox."""
    base = tmp_path / "sandbox"
    overrides = {
        "app_dir": base / "App",
        "watch_dir": base / "Upload",
        "dest_dir": base / "Data",
        "rename_dir": base / "Data" / "00_To_Rename",
        "exceptions_dir": base / "Data" / "01_Exceptions",
        "daily_records_json": base / "records.json",
    }

    pc = build_pc_config(override_paths=overrides)

    device = build_extr_haake_config()
    # Be patient for safe-save reappearance; other devices remain unaffected in this test
    device = replace(
        device,
        watcher=replace(
            device.watcher,
            poll_seconds=0.2,
            stable_cycles=2,
            max_wait_seconds=10.0,
            # New field to be added in TDD: allow disappear/reappear grace
            reappear_window_seconds=5.0,  # type: ignore[arg-type]
        ),
    )

    service = init_config(pc, [device])

    ui = HeadlessUI()
    sync = DummySyncManager(ui)
    init_dirs()

    # Use stub observer so we can drive events ourselves
    observer_stub = FakeObserver()

    app = DeviceWatchdogApp(
        ui=cast(Any, ui),
        sync_manager=sync,
        config_service=service,
        file_process_manager_cls=FileProcessManager,
    )

    # Monkeypatch the Observer factory used by the app.
    app_mod = importlib.import_module(DeviceWatchdogApp.__module__)
    app_mod.Observer = lambda: observer_stub  # type: ignore[assignment]

    app.initialize()
    try:
        yield app
    finally:
        app.on_closing()
        reset_service()


def _delayed_write(target: Path, payload: bytes, delay: float = 1.0) -> None:
    def writer():
        time.sleep(delay)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    t = threading.Thread(target=writer, daemon=True)
    t.start()


def test_excel_safe_save_sequence_is_eventually_processed(app_with_extr_haake, tmp_path):
    app = app_with_extr_haake
    watch = app.watch_dir

    # Simulate: initial create -> immediate delete -> temp folder create/delete -> final file appears
    final_name = "usr-ipat-sample.xlsx"
    initial_path = Path(watch) / final_name

    # Initial short-lived create and delete
    initial_path.parent.mkdir(parents=True, exist_ok=True)
    initial_path.write_bytes(b"draft")
    initial_path.unlink()  # disappears before stability

    # A transient 8-hex temp folder (Excel-like) appears and disappears
    temp_dir = Path(watch) / "BE70CE10"
    temp_dir.mkdir(parents=True, exist_ok=True)
    (temp_dir / "tempfile.tmp").write_bytes(b"tmp")
    # Remove temp dir quickly
    for child in temp_dir.glob("*"):
        try:
            child.unlink()
        except Exception:
            pass
    try:
        temp_dir.rmdir()
    except Exception:
        pass

    # Schedule the real final file to appear shortly after processing starts
    final_path = Path(watch) / final_name
    _delayed_write(final_path, b"final content", delay=0.8)

    # Drive processing for the initial (now-missing) path; under the new behavior, this should wait
    app.file_processing.process_item(str(initial_path))

    # Allow any scheduled UI tasks to run and processing to complete
    drain_scheduled_tasks(app.ui)

    # The pipeline should not have rejected to exceptions; it should end up processed once the file reappears
    exceptions = list((Path(app.config_service.pc.paths.exceptions_dir)).glob("*.xlsx"))
    assert not exceptions, f"Unexpected exceptions bucket entries: {exceptions}"

    # Verify destination contains one processed .xlsx
    dest_root = Path(app.config_service.pc.paths.dest_dir)
    processed = list(dest_root.rglob("*.xlsx"))
    assert len(processed) == 1, f"Expected one processed xlsx, found {processed}"
    assert processed[0].read_bytes() == b"final content"
