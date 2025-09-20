from pathlib import Path

import pytest

from ipat_watchdog.core.config.settings_store import SettingsStore
from ipat_watchdog.core.processing.file_process_manager import FileProcessManager
from ipat_watchdog.core.processing.models import ProcessingCandidate, ProcessingStatus
from ipat_watchdog.core.processing.stability_tracker import StabilityOutcome
from ipat_watchdog.core.processing.file_processor_abstract import ProcessingOutput
from ipat_watchdog.core.processing.stability_tracker import FileStabilityTracker
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


@pytest.fixture
def manager(tmp_settings, monkeypatch) -> FileProcessManager:
    ui = HeadlessUI()
    sync = DummySyncManager(ui)
    session = FakeSessionManager()
    settings_manager = SettingsStore.get_manager()
    settings_manager.set_current_device(tmp_settings)

    # Avoid waits in tests by forcing stability tracker to report immediately stable
    monkeypatch.setattr(
        FileStabilityTracker,
        "wait",
        lambda self: StabilityOutcome(path=self.file_path, stable=True),
    )

    processor = DummyProcessor()
    mgr = FileProcessManager(
        interactions=ui,
        sync_manager=sync,
        session_manager=session,
        settings_manager=settings_manager,
        file_processor=processor,
    )
    return mgr


def test_process_item_deferred_when_preprocessing_pauses(manager, tmp_settings):
    manager.file_processor = DeferredProcessor()
    src = tmp_settings.WATCH_DIR / "abc-ipat-sample.txt"
    src.write_text("data")

    result = manager.process_item(str(src))
    assert result.status is ProcessingStatus.DEFERRED
    assert src.exists()


def test_process_item_rejects_unknown_device(manager, tmp_settings):
    settings_manager = SettingsStore.get_manager()
    settings_manager.set_current_device(None)

    src = tmp_settings.WATCH_DIR / "abc-ipat-sample.bad"
    src.write_text("data")

    result = manager.process_item(str(src))
    assert result.status is ProcessingStatus.REJECTED
    rejected = manager.get_and_clear_rejected()
    assert rejected and rejected[0][0] == str(src)


def test_add_item_to_record_success(manager, tmp_settings):
    settings_manager = SettingsStore.get_manager()
    settings_manager.set_current_device(tmp_settings)

    prefix = "abc-ipat-sample"
    result_path = manager.add_item_to_record(
        record=None,
        src_path=str(tmp_settings.WATCH_DIR / f"{prefix}.txt"),
        filename_prefix=prefix,
        extension=".txt",
        file_processor=manager.file_processor,
        notify=False,
    )
    assert result_path.endswith("dummy_file.txt")


def test_add_item_to_record_failure_raises(manager, tmp_settings):
    manager.file_processor = ErroringProcessor()
    with pytest.raises(RuntimeError):
        manager.add_item_to_record(
            record=None,
            src_path=str(tmp_settings.WATCH_DIR / "abc-ipat-sample.txt"),
            filename_prefix="abc-ipat-sample",
            extension=".txt",
            file_processor=manager.file_processor,
            notify=False,
        )


def test_invoke_rename_flow_cancel_moves_to_manual(manager, tmp_settings):
    manager.interactions.show_rename_dialog_return = None
    settings_manager = SettingsStore.get_manager()
    settings_manager.set_current_device(tmp_settings)

    src = tmp_settings.WATCH_DIR / "badprefix.tif"
    src.write_bytes(b"x")

    candidate = ProcessingCandidate(
        original_path=src,
        effective_path=src,
        prefix="badprefix",
        extension=".tif",
        processor=manager.file_processor,
        device_settings=tmp_settings,
        preprocessed_path=None,
    )

    result = manager._invoke_rename_flow(candidate, "badprefix", ".tif")
    assert result.status is ProcessingStatus.REJECTED
    rename_files = list(tmp_settings.RENAME_DIR.glob("badprefix*"))
    assert rename_files
    assert not src.exists()
