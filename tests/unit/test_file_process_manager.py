from pathlib import Path

import pytest

from ipat_watchdog.core.config import activate_device
from ipat_watchdog.core.processing.file_process_manager import FileProcessManager
from ipat_watchdog.core.processing.models import ProcessingCandidate, ProcessingStatus
from ipat_watchdog.core.processing.stability_tracker import StabilityOutcome, FileStabilityTracker
from ipat_watchdog.core.processing.file_processor_abstract import ProcessingOutput
from ipat_watchdog.core.processing.models import ProcessingResult
from tests.helpers.fake_session import FakeSessionManager
from tests.helpers.fake_sync import DummySyncManager
from tests.helpers.fake_ui import HeadlessUI
from tests.helpers.fake_processor import DummyProcessor


class DeferredProcessor(DummyProcessor):
    def device_specific_preprocessing(self, src_path: str) -> str | None:
        return None


class ErroringProcessor(DummyProcessor):
    def device_specific_processing(self, src_path: str, record_path: str, file_id: str, extension: str) -> ProcessingOutput:
        raise RuntimeError("boom")


class StagedSuffixProcessor(DummyProcessor):
    def device_specific_preprocessing(self, src_path: str) -> str:
        path = Path(src_path)
        staged = path.with_name(f"{path.stem}.__staged__{path.suffix}")
        staged.write_text("prepared")
        return str(staged)


@pytest.fixture
def manager_components(config_service, monkeypatch):
    ui = HeadlessUI()
    sync = DummySyncManager(ui)
    session = FakeSessionManager(interactions=ui, scheduler=ui)

    monkeypatch.setattr(
        FileStabilityTracker,
        "wait",
        lambda self: StabilityOutcome(path=self.file_path, stable=True),
    )

    manager = FileProcessManager(
        interactions=ui,
        sync_manager=sync,
        session_manager=session,
        config_service=config_service,
        file_processor=DummyProcessor(),
    )
    return manager, ui


def test_process_item_deferred_when_preprocessing_pauses(manager_components, config_service, tmp_settings):
    manager, _ = manager_components
    manager.file_processor = DeferredProcessor()

    src = tmp_settings.WATCH_DIR / "abc-ipat-sample.txt"
    src.write_text("data")

    result = manager.process_item(str(src))
    assert result.status is ProcessingStatus.DEFERRED
    assert src.exists()


def test_process_item_rejects_unknown_device(manager_components, config_service, tmp_settings):
    manager, _ = manager_components

    src = tmp_settings.WATCH_DIR / "abc-ipat-sample.bad"
    src.write_text("data")

    result = manager.process_item(str(src))
    assert result.status is ProcessingStatus.REJECTED
    rejected = manager.get_and_clear_rejected()
    assert rejected and rejected[0][0] == str(src)


def test_add_item_to_record_success(manager_components, config_service, tmp_settings):
    manager, _ = manager_components
    prefix = "abc-ipat-sample"

    with activate_device(config_service.devices[0]):
        result_path = manager.add_item_to_record(
            record=None,
            src_path=str(tmp_settings.WATCH_DIR / f"{prefix}.txt"),
            filename_prefix=prefix,
            extension=".txt",
            file_processor=manager.file_processor,
            notify=False,
        )

    assert result_path.endswith("dummy_file.txt")


def test_add_item_to_record_failure_raises(manager_components, config_service, tmp_settings):
    manager, _ = manager_components
    manager.file_processor = ErroringProcessor()

    with activate_device(config_service.devices[0]):
        with pytest.raises(RuntimeError):
            manager.add_item_to_record(
                record=None,
                src_path=str(tmp_settings.WATCH_DIR / "abc-ipat-sample.txt"),
                filename_prefix="abc-ipat-sample",
                extension=".txt",
                file_processor=manager.file_processor,
                notify=False,
            )


def test_invoke_rename_flow_cancel_moves_to_manual(manager_components, config_service, tmp_settings):
    manager, ui = manager_components
    ui.show_rename_dialog_return = None

    src = tmp_settings.WATCH_DIR / "badprefix.tif"
    src.write_bytes(b"x")

    device = config_service.devices[0]
    candidate = ProcessingCandidate(
        original_path=src,
        effective_path=src,
        prefix="badprefix",
        extension=".tif",
        processor=manager.file_processor,
        device=device,
        preprocessed_path=None,
    )

    result = manager._pipeline._invoke_rename_flow(candidate, "badprefix", ".tif")
    assert result.status is ProcessingStatus.REJECTED
    rename_files = list(tmp_settings.RENAME_DIR.glob("badprefix*"))
    assert rename_files
    assert not src.exists()

@pytest.mark.parametrize(
    "path_name",
    [
        "file.__staged__",
        "file.__staged__1",
        "file.__staged__.txt",
        "file.__STAGED__2.tif",
        "file.__staged__ (1).txt",
        "dir/.__staged__/file.tif",
        "dir/child.__staged__/file.tif",
    ],
)
def test_process_item_ignores_internal_staging_paths(manager_components, tmp_settings, path_name):
    manager, _ = manager_components
    target = tmp_settings.WATCH_DIR / path_name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"data")

    result = manager.process_item(str(target))

    assert result.status is ProcessingStatus.DEFERRED
    assert "internal staging" in result.message



def test_is_internal_staging_path_detects_nested():
    nested = Path("/tmp/Folder.__staged__/child/file.txt")
    assert FileProcessManager._is_internal_staging_path(nested) is True

    suffixed = Path("/tmp/sample.__staged__.tif")
    suffixed_counter = Path("/tmp/sample.__STAGED__5.tif")
    duped = Path("/tmp/sample.__staged__ (1).txt")
    assert FileProcessManager._is_internal_staging_path(suffixed) is True
    assert FileProcessManager._is_internal_staging_path(suffixed_counter) is True
    assert FileProcessManager._is_internal_staging_path(duped) is True
