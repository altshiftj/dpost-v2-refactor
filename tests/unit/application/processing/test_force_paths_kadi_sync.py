from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from dpost.application.config import activate_device
from dpost.application.naming.policy import generate_file_id, generate_record_id
from dpost.application.processing.file_process_manager import FileProcessManager
from dpost.application.processing.file_processor_abstract import ProcessingOutput
from dpost.infrastructure.storage.filesystem_utils import (
    get_record_path,
    get_unique_filename,
)
from dpost.infrastructure.sync.kadi_manager import KadiSyncManager
from tests.helpers.fake_processor import DummyProcessor
from tests.helpers.fake_session import FakeSessionManager
from tests.helpers.fake_sync import DummySyncManager
from tests.helpers.fake_ui import HeadlessUI


def test_force_paths_use_force_flag_in_kadi_sync(config_service, tmp_settings, monkeypatch):
    class DummyKadiManager:
        def __init__(self):
            pass

    monkeypatch.setattr(
        "dpost.infrastructure.sync.kadi_manager.KadiManager",
        DummyKadiManager,
    )

    ui = HeadlessUI()
    sync_mgr = DummySyncManager(ui)
    session = FakeSessionManager(interactions=ui, scheduler=ui)

    class ForcePathsProcessor(DummyProcessor):
        def device_specific_processing(
            self,
            src_path: str,
            record_path: str,
            file_id: str,
            extension: str,
        ) -> ProcessingOutput:
            record_dir = Path(record_path)
            record_dir.mkdir(parents=True, exist_ok=True)
            measurement = get_unique_filename(str(record_dir), file_id, extension)
            Path(measurement).write_text("measurement")

            cc_dest = record_dir / f"{file_id}-cc.csv"
            cc_dest.write_text("cc-data")
            agg_dest = record_dir / f"{file_id}-results.csv"
            agg_dest.write_text("agg-data")

            return ProcessingOutput(
                final_path=measurement,
                datatype="hioki",
                force_paths=(str(cc_dest), str(agg_dest)),
            )

    manager = FileProcessManager(
        interactions=ui,
        sync_manager=sync_mgr,
        session_manager=session,
        config_service=config_service,
        file_processor=ForcePathsProcessor(),
    )

    prefix = "abc-ipat-sample"
    src = tmp_settings.WATCH_DIR / f"{prefix}.csv"
    src.write_text("data")

    device = config_service.devices[0]
    with activate_device(device):
        manager.add_item_to_record(
            record=None,
            src_path=str(src),
            filename_prefix=prefix,
            extension=".csv",
            file_processor=manager.file_processor,
        )

    device_abbr = device.metadata.device_abbr
    active = manager.config_service.current
    record_path = get_record_path(
        prefix,
        device_abbr,
        id_separator=active.id_separator,
        dest_dir=active.paths.dest_dir,
        current_device=manager.config_service.current_device(),
    )
    file_id = generate_file_id(prefix, device_abbr, id_separator="-")
    cc_path = str(Path(record_path) / f"{file_id}-cc.csv")
    agg_path = str(Path(record_path) / f"{file_id}-results.csv")

    record_id = generate_record_id(
        prefix,
        dev_kadi_record_id=device.metadata.record_kadi_id,
        id_separator="-",
    )
    record = manager.records.get_record_by_id(record_id)
    assert record is not None

    dummy_record = MagicMock()
    kadi_sync = KadiSyncManager(interactions=ui)

    kadi_sync._upload_record_files(dummy_record, record)

    dummy_record.upload_file.assert_any_call(cc_path, force=True)
    dummy_record.upload_file.assert_any_call(agg_path, force=True)


def test_force_paths_relative_to_record_dir_are_forced(config_service, tmp_settings):
    ui = HeadlessUI()
    sync_mgr = DummySyncManager(ui)
    session = FakeSessionManager(interactions=ui, scheduler=ui)

    class RelativeForcePathsProcessor(DummyProcessor):
        def device_specific_processing(
            self,
            src_path: str,
            record_path: str,
            file_id: str,
            extension: str,
        ) -> ProcessingOutput:
            record_dir = Path(record_path)
            record_dir.mkdir(parents=True, exist_ok=True)
            measurement = get_unique_filename(str(record_dir), file_id, extension)
            Path(measurement).write_text("measurement")

            cc_name = f"{file_id}-cc.csv"
            agg_name = f"{file_id}-results.csv"
            (record_dir / cc_name).write_text("cc-data")
            (record_dir / agg_name).write_text("agg-data")

            return ProcessingOutput(
                final_path=measurement,
                datatype="hioki",
                force_paths=(cc_name, agg_name),
            )

    manager = FileProcessManager(
        interactions=ui,
        sync_manager=sync_mgr,
        session_manager=session,
        config_service=config_service,
        file_processor=RelativeForcePathsProcessor(),
    )

    prefix = "abc-ipat-sample"
    src = tmp_settings.WATCH_DIR / f"{prefix}.csv"
    src.write_text("data")

    device = config_service.devices[0]
    with activate_device(device):
        manager.add_item_to_record(
            record=None,
            src_path=str(src),
            filename_prefix=prefix,
            extension=".csv",
            file_processor=manager.file_processor,
        )

    device_abbr = device.metadata.device_abbr
    active = manager.config_service.current
    record_path = get_record_path(
        prefix,
        device_abbr,
        id_separator=active.id_separator,
        dest_dir=active.paths.dest_dir,
        current_device=manager.config_service.current_device(),
    )
    file_id = generate_file_id(prefix, device_abbr, id_separator="-")
    cc_path = str(Path(record_path) / f"{file_id}-cc.csv")
    agg_path = str(Path(record_path) / f"{file_id}-results.csv")

    record_id = generate_record_id(
        prefix,
        dev_kadi_record_id=device.metadata.record_kadi_id,
        id_separator="-",
    )
    record = manager.records.get_record_by_id(record_id)
    assert record is not None

    assert cc_path in record.files_require_force
    assert agg_path in record.files_require_force
