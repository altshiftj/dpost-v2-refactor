from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from dpost.application.config.context import init_config, reset_service
from dpost.application.naming.policy import generate_file_id, generate_record_id
from dpost.application.processing.file_process_manager import FileProcessManager
from dpost.application.processing.stability_tracker import (
    FileStabilityTracker,
    StabilityOutcome,
)
from dpost.device_plugins.erm_hioki.file_processor import FileProcessorHioki
from dpost.device_plugins.erm_hioki.settings import build_config as build_hioki_config
from dpost.infrastructure.storage.filesystem_utils import (
    get_record_path,
    get_unique_filename,
    init_dirs,
)
from dpost.pc_plugins.test_pc.settings import build_config as build_pc_config
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
    init_dirs([str(path) for path in service.current.directory_list])

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

    yield manager, device_config, SimpleNamespace(
        WATCH_DIR=watch_dir, DEST_DIR=dest_dir
    )
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

    device_abbr = device_config.metadata.device_abbr
    active = manager.config_service.current
    record_path = get_record_path(
        prefix,
        device_abbr,
        id_separator=active.id_separator,
        dest_dir=active.paths.dest_dir,
        current_device=manager.config_service.current_device(),
    )
    file_id = generate_file_id(prefix, device_abbr, id_separator="-")
    expected_measurement = get_unique_filename(
        record_path,
        file_id,
        ".csv",
        id_separator="-",
    )

    manager.process_item(str(measurement))

    assert Path(expected_measurement).exists()
    assert not measurement.exists()


def test_measurement_creates_second_file_when_aggregate_exists(hioki_manager):
    manager, device_config, paths = hioki_manager
    prefix = "jfi-ipat-hioki_test"

    measurement_one = paths.WATCH_DIR / f"{prefix}_20260114183851.csv"
    measurement_one.write_text("measurement-1")
    aggregate = paths.WATCH_DIR / f"{prefix}.csv"
    aggregate.write_text("agg-data")
    cc_file = paths.WATCH_DIR / f"CC_{prefix}.csv"
    cc_file.write_text("cc-data")

    device_abbr = device_config.metadata.device_abbr
    active = manager.config_service.current
    record_path = get_record_path(
        prefix,
        device_abbr,
        id_separator=active.id_separator,
        dest_dir=active.paths.dest_dir,
        current_device=manager.config_service.current_device(),
    )
    file_id = generate_file_id(prefix, device_abbr, id_separator="-")
    expected_first = get_unique_filename(
        record_path,
        file_id,
        ".csv",
        id_separator="-",
    )

    manager.process_item(str(measurement_one))
    assert Path(expected_first).exists()

    measurement_two = paths.WATCH_DIR / f"{prefix}_20260114183941.csv"
    measurement_two.write_text("measurement-2")
    expected_second = get_unique_filename(
        record_path,
        file_id,
        ".csv",
        id_separator="-",
    )

    manager.process_item(str(measurement_two))

    assert Path(expected_second).exists()
    assert not measurement_two.exists()


def test_aggregate_update_marks_force_after_upload(hioki_manager):
    manager, device_config, paths = hioki_manager
    prefix = "jfi-ipat-hioki_test"

    aggregate = paths.WATCH_DIR / f"{prefix}.csv"
    aggregate.write_text("agg-1")

    manager.process_item(str(aggregate))

    device_abbr = device_config.metadata.device_abbr
    active = manager.config_service.current
    record_path = get_record_path(
        prefix,
        device_abbr,
        id_separator=active.id_separator,
        dest_dir=active.paths.dest_dir,
        current_device=manager.config_service.current_device(),
    )
    file_id = generate_file_id(prefix, device_abbr, id_separator="-")
    results_path = Path(record_path) / f"{file_id}-results.csv"
    record_id = generate_record_id(
        prefix,
        dev_kadi_record_id=device_config.metadata.record_kadi_id,
        id_separator="-",
    )
    record = manager.records.get_record_by_id(record_id)
    assert record is not None

    record.mark_uploaded(results_path)
    aggregate.write_text("agg-2")
    manager.process_item(str(aggregate))

    assert str(results_path.resolve()) in record.files_require_force


def test_cc_update_marks_force_after_upload(hioki_manager):
    manager, device_config, paths = hioki_manager
    prefix = "jfi-ipat-hioki_test"

    cc_file = paths.WATCH_DIR / f"CC_{prefix}.csv"
    cc_file.write_text("cc-1")

    manager.process_item(str(cc_file))

    device_abbr = device_config.metadata.device_abbr
    active = manager.config_service.current
    record_path = get_record_path(
        prefix,
        device_abbr,
        id_separator=active.id_separator,
        dest_dir=active.paths.dest_dir,
        current_device=manager.config_service.current_device(),
    )
    file_id = generate_file_id(prefix, device_abbr, id_separator="-")
    cc_path = Path(record_path) / f"{file_id}-cc.csv"
    record_id = generate_record_id(
        prefix,
        dev_kadi_record_id=device_config.metadata.record_kadi_id,
        id_separator="-",
    )
    record = manager.records.get_record_by_id(record_id)
    assert record is not None

    record.mark_uploaded(cc_path)
    cc_file.write_text("cc-2")
    manager.process_item(str(cc_file))

    assert str(cc_path.resolve()) in record.files_require_force


def test_full_lab_sequence_marks_measurements_and_force_updates(hioki_manager):
    manager, device_config, paths = hioki_manager
    prefix = "jfi-ipat-hioki_test"
    device_abbr = device_config.metadata.device_abbr
    active = manager.config_service.current
    record_path = Path(
        get_record_path(
            prefix,
            device_abbr,
            id_separator=active.id_separator,
            dest_dir=active.paths.dest_dir,
            current_device=manager.config_service.current_device(),
        )
    )
    file_id = generate_file_id(prefix, device_abbr, id_separator="-")
    record_id = generate_record_id(
        prefix,
        dev_kadi_record_id=device_config.metadata.record_kadi_id,
        id_separator="-",
    )

    # 1) Initial CC
    cc_file = paths.WATCH_DIR / f"CC_{prefix}.csv"
    cc_file.write_text("cc-1")
    manager.process_item(str(cc_file))
    cc_dest = record_path / f"{file_id}-cc.csv"
    assert cc_dest.exists()
    assert cc_dest.read_text() == "cc-1"

    # 2) Measurement #1 before aggregate
    meas1 = paths.WATCH_DIR / f"{prefix}_20260114183851.csv"
    meas1.write_text("m1")
    expected_meas1 = Path(
        get_unique_filename(
            str(record_path),
            file_id,
            ".csv",
            id_separator="-",
        )
    )
    manager.process_item(str(meas1))
    assert expected_meas1.exists()
    assert expected_meas1.read_text() == "m1"

    # 3) Aggregate arrives
    agg_file = paths.WATCH_DIR / f"{prefix}.csv"
    agg_file.write_text("agg-1")
    manager.process_item(str(agg_file))
    results_path = record_path / f"{file_id}-results.csv"
    assert results_path.exists()
    assert results_path.read_text() == "agg-1"

    # Mark synced baseline
    record = manager.records.get_record_by_id(record_id)
    assert record is not None
    record.mark_uploaded(cc_dest)
    record.mark_uploaded(results_path)

    # 4) Measurement #2 should create -02
    meas2 = paths.WATCH_DIR / f"{prefix}_20260114183941.csv"
    meas2.write_text("m2")
    expected_meas2 = Path(
        get_unique_filename(
            str(record_path),
            file_id,
            ".csv",
            id_separator="-",
        )
    )
    manager.process_item(str(meas2))
    assert expected_meas2.exists()
    assert expected_meas2.read_text() == "m2"

    # 5) Aggregate update should mark force
    agg_file.write_text("agg-2")
    manager.process_item(str(agg_file))
    assert results_path.read_text() == "agg-2"
    assert str(results_path.resolve()) in record.files_require_force

    # 6) CC update should mark force
    cc_file.write_text("cc-2")
    manager.process_item(str(cc_file))
    assert cc_dest.read_text() == "cc-2"
    assert str(cc_dest.resolve()) in record.files_require_force
