"""Migration tests for Phase 5 processing stage-boundary decomposition."""

from __future__ import annotations

from pathlib import Path

import pytest

from ipat_watchdog.core.processing.file_process_manager import (
    FileProcessManager,
    _ProcessingPipeline,
)
from ipat_watchdog.core.processing.models import (
    ProcessingCandidate,
    ProcessingRequest,
    ProcessingResult,
    ProcessingStatus,
    RouteContext,
    RoutingDecision,
)
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


def test_pipeline_declares_preprocess_stage_hook() -> None:
    """Require an explicit preprocess seam method for incremental extraction."""
    assert hasattr(_ProcessingPipeline, "_preprocess_stage")


def test_execute_pipeline_delegates_to_preprocess_stage_hook(
    process_manager: FileProcessManager,
    config_service,
    tmp_settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Call preprocess stage hook before route context and dispatch steps."""
    pipeline = process_manager._pipeline
    source = tmp_settings.WATCH_DIR / "abc-ipat-sample.txt"
    source.write_text("payload")
    request = ProcessingRequest(source=source, device=config_service.devices[0])
    calls: list[str] = []
    sentinel_processor = DummyProcessor()
    sentinel_candidate = object()

    def resolve_processor(device):
        calls.append("resolve_processor")
        assert device == request.device
        return sentinel_processor

    def preprocess_stage(preprocess_request, processor):
        calls.append("preprocess")
        assert preprocess_request == request
        assert processor is sentinel_processor
        return sentinel_candidate

    def build_route_context(candidate):
        calls.append("build_route_context")
        assert candidate is sentinel_candidate
        return "route-context"

    def dispatch_route(route_context):
        calls.append("dispatch_route")
        assert route_context == "route-context"
        return ProcessingResult(ProcessingStatus.PROCESSED, "processed")

    monkeypatch.setattr(process_manager, "_resolve_processor", resolve_processor)
    monkeypatch.setattr(pipeline, "_preprocess_stage", preprocess_stage, raising=False)
    monkeypatch.setattr(
        pipeline,
        "_build_candidate",
        lambda *_args, **_kwargs: pytest.fail(
            "Legacy _build_candidate call should move behind _preprocess_stage."
        ),
    )
    monkeypatch.setattr(pipeline, "_build_route_context", build_route_context)
    monkeypatch.setattr(pipeline, "_dispatch_route", dispatch_route)

    result = pipeline._execute_pipeline(request)

    assert result.status is ProcessingStatus.PROCESSED
    assert calls == [
        "resolve_processor",
        "preprocess",
        "build_route_context",
        "dispatch_route",
    ]


def test_pipeline_declares_persist_and_sync_stage_hook() -> None:
    """Require explicit persist/sync seam method for route separation."""
    assert hasattr(_ProcessingPipeline, "_persist_and_sync_stage")


def test_dispatch_route_accept_delegates_to_persist_and_sync_stage(
    process_manager: FileProcessManager,
    config_service,
    tmp_settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Delegate ACCEPT route side effects through persist/sync stage hook."""
    pipeline = process_manager._pipeline
    source = tmp_settings.WATCH_DIR / "abc-ipat-sample.txt"
    source.write_text("payload")
    candidate = ProcessingCandidate(
        original_path=source,
        effective_path=source,
        prefix="abc-ipat-sample",
        extension=".txt",
        processor=DummyProcessor(),
        device=config_service.devices[0],
        preprocessed_path=None,
    )
    context = RouteContext(
        candidate=candidate,
        sanitized_prefix="abc-ipat-sample",
        existing_record=None,
        decision=RoutingDecision.ACCEPT,
    )
    calls: list[str] = []

    def persist_stage(route_context: RouteContext) -> ProcessingResult:
        calls.append("persist")
        assert route_context is context
        return ProcessingResult(ProcessingStatus.PROCESSED, "processed")

    monkeypatch.setattr(
        pipeline,
        "_persist_and_sync_stage",
        persist_stage,
        raising=False,
    )
    monkeypatch.setattr(
        process_manager,
        "add_item_to_record",
        lambda *_args, **_kwargs: pytest.fail(
            "ACCEPT path should delegate persistence through _persist_and_sync_stage."
        ),
    )

    result = pipeline._dispatch_route(context)

    assert result.status is ProcessingStatus.PROCESSED
    assert calls == ["persist"]


def test_pipeline_declares_route_decision_stage_hook() -> None:
    """Require explicit route-decision seam method for decomposition."""
    assert hasattr(_ProcessingPipeline, "_route_decision_stage")


def test_route_with_prefix_delegates_accept_without_dispatch(
    process_manager: FileProcessManager,
    config_service,
    tmp_settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resolve route decision and persist without redispatching through `_dispatch_route`."""
    pipeline = process_manager._pipeline
    source = tmp_settings.WATCH_DIR / "abc-ipat-sample.txt"
    source.write_text("payload")
    candidate = ProcessingCandidate(
        original_path=source,
        effective_path=source,
        prefix="abc-ipat-sample",
        extension=".txt",
        processor=DummyProcessor(),
        device=config_service.devices[0],
        preprocessed_path=None,
    )
    expected_context = RouteContext(
        candidate=candidate,
        sanitized_prefix="abc-ipat-sample",
        existing_record=None,
        decision=RoutingDecision.ACCEPT,
    )
    calls: list[str] = []

    def route_decision_stage(route_candidate: ProcessingCandidate) -> RouteContext:
        calls.append("route_decision")
        assert route_candidate.prefix == "abc-ipat-sample"
        return expected_context

    def persist_stage(route_context: RouteContext) -> ProcessingResult:
        calls.append("persist")
        assert route_context is expected_context
        return ProcessingResult(ProcessingStatus.PROCESSED, "processed")

    monkeypatch.setattr(
        pipeline,
        "_route_decision_stage",
        route_decision_stage,
        raising=False,
    )
    monkeypatch.setattr(pipeline, "_persist_and_sync_stage", persist_stage)
    monkeypatch.setattr(
        pipeline,
        "_dispatch_route",
        lambda *_args, **_kwargs: pytest.fail(
            "_route_with_prefix should not redispatch through _dispatch_route."
        ),
    )

    result = pipeline._route_with_prefix(candidate, "abc-ipat-sample")

    assert result.status is ProcessingStatus.PROCESSED
    assert calls == ["route_decision", "persist"]
