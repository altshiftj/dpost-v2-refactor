"""Migration tests for Phase 5 processing stage-boundary decomposition."""

from __future__ import annotations

from pathlib import Path

import pytest

from ipat_watchdog.core.processing.file_process_manager import (
    FileProcessManager,
    _ProcessingPipeline,
)
from ipat_watchdog.core.processing.models import ProcessingResult, ProcessingStatus
from tests.helpers.fake_processor import DummyProcessor
from tests.helpers.fake_session import FakeSessionManager
from tests.helpers.fake_sync import DummySyncManager
from tests.helpers.fake_ui import HeadlessUI


@pytest.fixture
def process_manager(config_service):
    """Build a minimal manager for pipeline boundary characterization tests."""
    ui = HeadlessUI()
    sync = DummySyncManager(ui)
    session = FakeSessionManager(interactions=ui, scheduler=ui)
    return FileProcessManager(
        interactions=ui,
        sync_manager=sync,
        session_manager=session,
        config_service=config_service,
        file_processor=DummyProcessor(),
    )


def test_pipeline_declares_resolve_and_stabilize_stage_hooks() -> None:
    """Require explicit resolve/stabilize seam methods for incremental extraction."""
    assert hasattr(_ProcessingPipeline, "_resolve_device_stage")
    assert hasattr(_ProcessingPipeline, "_stabilize_artifact_stage")


def test_process_delegates_to_resolve_then_stabilize_stage_hooks(
    process_manager: FileProcessManager,
    tmp_settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Call resolve and stabilize stage hooks in order before pipeline execution."""
    pipeline = process_manager._pipeline
    source = tmp_settings.WATCH_DIR / "abc-ipat-sample.txt"
    source.write_text("payload")
    calls: list[str] = []

    def resolve_stage(path: Path):
        calls.append("resolve")
        assert path == source
        return "resolved-request"

    def stabilize_stage(request: str):
        calls.append("stabilize")
        assert request == "resolved-request"
        return "stable-request"

    def execute_stage(request: str) -> ProcessingResult:
        calls.append("execute")
        assert request == "stable-request"
        return ProcessingResult(ProcessingStatus.PROCESSED, "processed")

    monkeypatch.setattr(pipeline, "_resolve_device_stage", resolve_stage, raising=False)
    monkeypatch.setattr(
        pipeline,
        "_stabilize_artifact_stage",
        stabilize_stage,
        raising=False,
    )
    monkeypatch.setattr(pipeline, "_execute_pipeline", execute_stage)
    monkeypatch.setattr(
        pipeline,
        "_prepare_request",
        lambda _path: pytest.fail(
            "Legacy _prepare_request path should be replaced by explicit stage hooks."
        ),
    )

    result = pipeline.process(source)

    assert result.status is ProcessingStatus.PROCESSED
    assert calls == ["resolve", "stabilize", "execute"]
