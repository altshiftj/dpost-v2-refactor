"""Migration tests for Phase 5 processing stage-boundary decomposition."""

from __future__ import annotations

import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest

from ipat_watchdog.core.processing.file_process_manager import (
    FileProcessManager,
    _ProcessingPipeline,
)
from ipat_watchdog.core.processing.file_processor_abstract import ProcessingOutput
from ipat_watchdog.core.processing.models import (
    ProcessingCandidate,
    ProcessingRequest,
    ProcessingResult,
    ProcessingStatus,
    RouteContext,
    RoutingDecision,
)
from ipat_watchdog.core.processing.rename_flow import RenameOutcome
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


def test_manager_declares_persist_candidate_record_stage_hook() -> None:
    """Require explicit manager seam for record persistence side effects."""
    assert hasattr(FileProcessManager, "_persist_candidate_record_stage")


def test_manager_declares_post_persist_side_effects_stage_hook() -> None:
    """Require explicit manager seam for post-persist bookkeeping side effects."""
    assert hasattr(FileProcessManager, "_post_persist_side_effects_stage")


def test_manager_declares_resolve_record_persistence_context_stage_hook() -> None:
    """Require explicit manager seam for record/processor context resolution."""
    assert hasattr(FileProcessManager, "_resolve_record_persistence_context_stage")


def test_manager_declares_process_record_artifact_stage_hook() -> None:
    """Require explicit manager seam for processor invocation/output handling."""
    assert hasattr(FileProcessManager, "_process_record_artifact_stage")


def test_manager_declares_assign_record_datatype_stage_hook() -> None:
    """Require explicit manager seam for datatype assignment policy."""
    assert hasattr(FileProcessManager, "_assign_record_datatype_stage")


def test_add_item_to_record_delegates_process_record_artifact_stage(
    process_manager: FileProcessManager,
    config_service,
    tmp_settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Delegate processor invocation/output handling to explicit seam."""
    src = tmp_settings.WATCH_DIR / "abc-ipat-sample.txt"
    src.write_text("payload")
    fake_record = SimpleNamespace(
        default_description="",
        default_tags=[],
        datatype=None,
    )
    calls: list[str] = []
    expected_output = ProcessingOutput(
        str(tmp_settings.WATCH_DIR / "processed.txt"),
        "dummy_type",
    )

    def resolve_record_persistence_context_stage(
        _record,
        _filename_prefix: str,
        _device,
        processor,
    ):
        return fake_record, processor, str(tmp_settings.WATCH_DIR), "test_file_id"

    def process_record_artifact_stage(
        _processor,
        src_path: str,
        record_path: str,
        file_id: str,
        extension: str,
    ) -> ProcessingOutput:
        calls.append("process_artifact")
        assert src_path == str(src)
        assert record_path == str(tmp_settings.WATCH_DIR)
        assert file_id == "test_file_id"
        assert extension == ".txt"
        return expected_output

    monkeypatch.setattr(
        process_manager,
        "_resolve_record_persistence_context_stage",
        resolve_record_persistence_context_stage,
        raising=False,
    )
    monkeypatch.setattr(
        process_manager,
        "_process_record_artifact_stage",
        process_record_artifact_stage,
        raising=False,
    )
    monkeypatch.setattr(
        process_manager.file_processor,
        "device_specific_processing",
        lambda *_args, **_kwargs: pytest.fail(
            "add_item_to_record should delegate processor invocation through "
            "_process_record_artifact_stage."
        ),
    )
    monkeypatch.setattr(
        process_manager,
        "_post_persist_side_effects_stage",
        lambda *_args, **_kwargs: None,
    )

    result = process_manager.add_item_to_record(
        record=None,
        src_path=str(src),
        filename_prefix="abc-ipat-sample",
        extension=".txt",
        file_processor=process_manager.file_processor,
        device=config_service.devices[0],
    )

    assert result == expected_output.final_path
    assert fake_record.datatype == "dummy_type"
    assert calls == ["process_artifact"]


def test_add_item_to_record_delegates_record_datatype_assignment_stage(
    process_manager: FileProcessManager,
    config_service,
    tmp_settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Delegate datatype assignment through explicit seam without inline mutation."""
    src = tmp_settings.WATCH_DIR / "abc-ipat-sample.txt"
    src.write_text("payload")
    fake_record = SimpleNamespace(
        default_description="",
        default_tags=[],
        datatype=None,
    )
    expected_output = ProcessingOutput(
        str(tmp_settings.WATCH_DIR / "processed.txt"),
        "dummy_type",
    )
    calls: list[str] = []

    def resolve_record_persistence_context_stage(
        _record,
        _filename_prefix: str,
        _device,
        processor,
    ):
        return fake_record, processor, str(tmp_settings.WATCH_DIR), "test_file_id"

    def process_record_artifact_stage(
        _processor,
        _src_path: str,
        _record_path: str,
        _file_id: str,
        _extension: str,
    ) -> ProcessingOutput:
        return expected_output

    def assign_record_datatype_stage(record, output: ProcessingOutput) -> None:
        calls.append("assign_datatype")
        assert record is fake_record
        assert output is expected_output
        # Intentionally no mutation: add_item_to_record must not set datatype inline.

    monkeypatch.setattr(
        process_manager,
        "_resolve_record_persistence_context_stage",
        resolve_record_persistence_context_stage,
        raising=False,
    )
    monkeypatch.setattr(
        process_manager,
        "_process_record_artifact_stage",
        process_record_artifact_stage,
        raising=False,
    )
    monkeypatch.setattr(
        process_manager,
        "_assign_record_datatype_stage",
        assign_record_datatype_stage,
        raising=False,
    )
    monkeypatch.setattr(
        process_manager,
        "_post_persist_side_effects_stage",
        lambda *_args, **_kwargs: None,
    )

    result = process_manager.add_item_to_record(
        record=None,
        src_path=str(src),
        filename_prefix="abc-ipat-sample",
        extension=".txt",
        file_processor=process_manager.file_processor,
        device=config_service.devices[0],
    )

    assert result == expected_output.final_path
    assert calls == ["assign_datatype"]
    assert fake_record.datatype is None


def test_add_item_to_record_delegates_resolve_record_persistence_context_stage(
    process_manager: FileProcessManager,
    config_service,
    tmp_settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Delegate record initialization and processor context to explicit seam."""
    src = tmp_settings.WATCH_DIR / "abc-ipat-sample.txt"
    src.write_text("payload")
    calls: list[str] = []
    fake_record = SimpleNamespace(
        default_description="", default_tags=[], datatype=None
    )

    class FakeProcessor(DummyProcessor):
        def __init__(self):
            super().__init__()
            self.processing_calls: list[tuple[str, str, str, str]] = []

        def device_specific_processing(
            self,
            src_path: str,
            record_path: str,
            file_id: str,
            extension: str,
        ):
            self.processing_calls.append((src_path, record_path, file_id, extension))
            return super().device_specific_processing(
                src_path, record_path, file_id, extension
            )

    fake_processor = FakeProcessor()

    def resolve_record_persistence_context_stage(
        _record,
        _filename_prefix: str,
        _device,
        _processor,
    ):
        calls.append("resolve_context")
        return fake_record, fake_processor, str(tmp_settings.WATCH_DIR), "test_file_id"

    monkeypatch.setattr(
        process_manager,
        "_resolve_record_persistence_context_stage",
        resolve_record_persistence_context_stage,
        raising=False,
    )
    monkeypatch.setattr(
        process_manager,
        "_post_persist_side_effects_stage",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "ipat_watchdog.core.processing.file_process_manager.get_or_create_record",
        lambda *_args, **_kwargs: pytest.fail(
            "add_item_to_record should delegate record setup through "
            "_resolve_record_persistence_context_stage."
        ),
    )
    monkeypatch.setattr(
        "ipat_watchdog.core.processing.file_process_manager.get_record_path",
        lambda *_args, **_kwargs: pytest.fail(
            "add_item_to_record should delegate record path resolution through "
            "_resolve_record_persistence_context_stage."
        ),
    )
    monkeypatch.setattr(
        "ipat_watchdog.core.processing.file_process_manager.generate_file_id",
        lambda *_args, **_kwargs: pytest.fail(
            "add_item_to_record should delegate file-id resolution through "
            "_resolve_record_persistence_context_stage."
        ),
    )

    result = process_manager.add_item_to_record(
        record=None,
        src_path=str(src),
        filename_prefix="abc-ipat-sample",
        extension=".txt",
        file_processor=process_manager.file_processor,
        device=config_service.devices[0],
    )

    assert result is not None
    assert calls == ["resolve_context"]
    assert fake_processor.processing_calls == [
        (str(src), str(tmp_settings.WATCH_DIR), "test_file_id", ".txt")
    ]


def test_add_item_to_record_delegates_post_persist_side_effects_stage(
    process_manager: FileProcessManager,
    config_service,
    tmp_settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Delegate record bookkeeping/sync side effects through stage seam."""
    src = tmp_settings.WATCH_DIR / "abc-ipat-sample.txt"
    src.write_text("payload")
    calls: list[str] = []

    def post_persist_side_effects_stage(
        *_args,
        **_kwargs,
    ) -> None:
        calls.append("post_persist")

    monkeypatch.setattr(
        process_manager,
        "_post_persist_side_effects_stage",
        post_persist_side_effects_stage,
        raising=False,
    )
    monkeypatch.setattr(
        "ipat_watchdog.core.processing.file_process_manager.update_record",
        lambda *_args, **_kwargs: pytest.fail(
            "add_item_to_record should delegate post-persist bookkeeping "
            "through _post_persist_side_effects_stage."
        ),
    )

    result = process_manager.add_item_to_record(
        record=None,
        src_path=str(src),
        filename_prefix="abc-ipat-sample",
        extension=".txt",
        file_processor=process_manager.file_processor,
        device=config_service.devices[0],
    )

    assert result is not None
    assert calls == ["post_persist"]


def test_persist_and_sync_stage_delegates_manager_persist_candidate_record_stage(
    process_manager: FileProcessManager,
    config_service,
    tmp_settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Delegate ACCEPT persistence through manager seam, not direct add-item calls."""
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
    expected_final_path = source.parent / "record" / "processed.txt"

    def persist_candidate_record_stage(route_context: RouteContext) -> str:
        calls.append("persist_candidate_record")
        assert route_context is context
        return str(expected_final_path)

    monkeypatch.setattr(
        process_manager,
        "_persist_candidate_record_stage",
        persist_candidate_record_stage,
        raising=False,
    )
    monkeypatch.setattr(
        process_manager,
        "add_item_to_record",
        lambda *_args, **_kwargs: pytest.fail(
            "_persist_and_sync_stage should delegate via "
            "_persist_candidate_record_stage."
        ),
    )

    result = pipeline._persist_and_sync_stage(context)

    assert result.status is ProcessingStatus.PROCESSED
    assert result.final_path == expected_final_path
    assert calls == ["persist_candidate_record"]


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


def test_pipeline_declares_non_accept_route_stage_hook() -> None:
    """Require explicit non-ACCEPT routing seam for decision-path clarity."""
    assert hasattr(_ProcessingPipeline, "_non_accept_route_stage")


def test_route_with_prefix_delegates_non_accept_without_dispatch(
    process_manager: FileProcessManager,
    config_service,
    tmp_settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resolve non-ACCEPT decision and delegate without redispatching."""
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
        decision=RoutingDecision.REQUIRE_RENAME,
    )
    calls: list[str] = []

    def route_decision_stage(route_candidate: ProcessingCandidate) -> RouteContext:
        calls.append("route_decision")
        assert route_candidate.prefix == "abc-ipat-sample"
        return expected_context

    def non_accept_stage(route_context: RouteContext) -> ProcessingResult:
        calls.append("non_accept")
        assert route_context is expected_context
        return ProcessingResult(ProcessingStatus.REJECTED, "rename-required")

    monkeypatch.setattr(
        pipeline,
        "_route_decision_stage",
        route_decision_stage,
        raising=False,
    )
    monkeypatch.setattr(
        pipeline,
        "_non_accept_route_stage",
        non_accept_stage,
        raising=False,
    )
    monkeypatch.setattr(
        pipeline,
        "_dispatch_route",
        lambda *_args, **_kwargs: pytest.fail(
            "_route_with_prefix should not redispatch through _dispatch_route."
        ),
    )

    result = pipeline._route_with_prefix(candidate, "abc-ipat-sample")

    assert result.status is ProcessingStatus.REJECTED
    assert calls == ["route_decision", "non_accept"]


def test_non_accept_route_stage_require_rename_avoids_recursive_route_with_prefix_reentry(
    process_manager: FileProcessManager,
    config_service,
    tmp_settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep rename retries from recursively re-entering `_route_with_prefix`."""
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
        decision=RoutingDecision.REQUIRE_RENAME,
    )

    rename_attempts = iter(("abc-ipat-retry1", "abc-ipat-retry2"))
    route_decisions = iter((RoutingDecision.REQUIRE_RENAME, RoutingDecision.ACCEPT))

    def obtain_valid_prefix(
        _current_prefix: str,
        _contextual_reason: str | None = None,
    ) -> RenameOutcome:
        return RenameOutcome(next(rename_attempts), cancelled=False)

    def route_decision_stage(route_candidate: ProcessingCandidate) -> RouteContext:
        return RouteContext(
            candidate=route_candidate,
            sanitized_prefix=route_candidate.prefix,
            existing_record=None,
            decision=next(route_decisions),
        )

    def persist_stage(_route_context: RouteContext) -> ProcessingResult:
        return ProcessingResult(ProcessingStatus.PROCESSED, "processed")

    original_route_with_prefix = pipeline._route_with_prefix
    is_active = False

    def guarded_route_with_prefix(
        route_candidate: ProcessingCandidate,
        prefix_override: str,
    ) -> ProcessingResult:
        nonlocal is_active
        if is_active:
            pytest.fail(
                "Rename retries should not recursively re-enter _route_with_prefix."
            )
        is_active = True
        try:
            return original_route_with_prefix(route_candidate, prefix_override)
        finally:
            is_active = False

    monkeypatch.setattr(
        process_manager._rename_service,
        "obtain_valid_prefix",
        obtain_valid_prefix,
    )
    monkeypatch.setattr(pipeline, "_route_decision_stage", route_decision_stage)
    monkeypatch.setattr(pipeline, "_persist_and_sync_stage", persist_stage)
    monkeypatch.setattr(
        pipeline,
        "_route_with_prefix",
        guarded_route_with_prefix,
        raising=False,
    )

    result = pipeline._non_accept_route_stage(context)

    assert result.status is ProcessingStatus.PROCESSED


def test_non_accept_route_stage_unappendable_avoids_recursive_route_with_prefix_reentry(
    process_manager: FileProcessManager,
    config_service,
    tmp_settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep unappendable rename retries from recursively re-entering `_route_with_prefix`."""
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
        decision=RoutingDecision.UNAPPENDABLE,
    )

    rename_attempts = iter(("abc-ipat-retry1", "abc-ipat-retry2"))
    route_decisions = iter((RoutingDecision.UNAPPENDABLE, RoutingDecision.ACCEPT))

    def obtain_valid_prefix(
        _current_prefix: str,
        _contextual_reason: str | None = None,
    ) -> RenameOutcome:
        return RenameOutcome(next(rename_attempts), cancelled=False)

    def route_decision_stage(route_candidate: ProcessingCandidate) -> RouteContext:
        return RouteContext(
            candidate=route_candidate,
            sanitized_prefix=route_candidate.prefix,
            existing_record=None,
            decision=next(route_decisions),
        )

    def persist_stage(_route_context: RouteContext) -> ProcessingResult:
        return ProcessingResult(ProcessingStatus.PROCESSED, "processed")

    original_route_with_prefix = pipeline._route_with_prefix
    is_active = False

    def guarded_route_with_prefix(
        route_candidate: ProcessingCandidate,
        prefix_override: str,
    ) -> ProcessingResult:
        nonlocal is_active
        if is_active:
            pytest.fail(
                "Rename retries should not recursively re-enter _route_with_prefix."
            )
        is_active = True
        try:
            return original_route_with_prefix(route_candidate, prefix_override)
        finally:
            is_active = False

    monkeypatch.setattr(
        process_manager._rename_service,
        "obtain_valid_prefix",
        obtain_valid_prefix,
    )
    monkeypatch.setattr(pipeline, "_route_decision_stage", route_decision_stage)
    monkeypatch.setattr(pipeline, "_persist_and_sync_stage", persist_stage)
    monkeypatch.setattr(
        pipeline,
        "_route_with_prefix",
        guarded_route_with_prefix,
        raising=False,
    )

    result = pipeline._non_accept_route_stage(context)

    assert result.status is ProcessingStatus.PROCESSED


def test_pipeline_declares_rename_retry_policy_stage_hook() -> None:
    """Require an explicit retry-policy seam for rename loop side effects."""
    assert hasattr(_ProcessingPipeline, "_rename_retry_policy_stage")


def test_invoke_rename_flow_delegates_retry_policy_stage_without_inline_warning(
    process_manager: FileProcessManager,
    config_service,
    tmp_settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Delegate unappendable retry policy via stage hook instead of inline warnings."""
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

    rename_attempts: list[tuple[str, str | None]] = []
    route_decisions = iter((RoutingDecision.UNAPPENDABLE, RoutingDecision.ACCEPT))
    policy_calls: list[str] = []

    def obtain_valid_prefix(
        current_prefix: str,
        contextual_reason: str | None = None,
    ) -> RenameOutcome:
        rename_attempts.append((current_prefix, contextual_reason))
        if len(rename_attempts) == 1:
            return RenameOutcome("abc-ipat-retry1", cancelled=False)
        return RenameOutcome("abc-ipat-final", cancelled=False)

    def route_decision_stage(route_candidate: ProcessingCandidate) -> RouteContext:
        decision = next(route_decisions)
        if decision is RoutingDecision.UNAPPENDABLE:
            return RouteContext(
                candidate=route_candidate,
                sanitized_prefix="locked-record",
                existing_record=None,
                decision=decision,
            )
        return RouteContext(
            candidate=route_candidate,
            sanitized_prefix=route_candidate.prefix,
            existing_record=None,
            decision=decision,
        )

    def rename_retry_policy_stage(
        route_context: RouteContext,
    ) -> tuple[str, str | None]:
        policy_calls.append("retry_policy")
        assert route_context.decision is RoutingDecision.UNAPPENDABLE
        return "policy-prefix", "policy-reason"

    def persist_stage(_route_context: RouteContext) -> ProcessingResult:
        return ProcessingResult(ProcessingStatus.PROCESSED, "processed")

    monkeypatch.setattr(
        process_manager._rename_service,
        "obtain_valid_prefix",
        obtain_valid_prefix,
    )
    monkeypatch.setattr(pipeline, "_route_decision_stage", route_decision_stage)
    monkeypatch.setattr(
        pipeline,
        "_rename_retry_policy_stage",
        rename_retry_policy_stage,
        raising=False,
    )
    monkeypatch.setattr(pipeline, "_persist_and_sync_stage", persist_stage)
    monkeypatch.setattr(
        process_manager.interactions,
        "show_warning",
        lambda *_args, **_kwargs: pytest.fail(
            "_invoke_rename_flow should delegate unappendable warning policy "
            "through _rename_retry_policy_stage."
        ),
    )

    result = pipeline._invoke_rename_flow(
        candidate, candidate.prefix, candidate.extension
    )

    assert result.status is ProcessingStatus.PROCESSED
    assert policy_calls == ["retry_policy"]
    assert rename_attempts == [
        ("abc-ipat-sample", None),
        ("policy-prefix", "policy-reason"),
    ]


def test_manager_add_item_to_record_signature_omits_notify_flag() -> None:
    """Retire legacy success-notification toggle from record persistence API."""
    parameters = inspect.signature(FileProcessManager.add_item_to_record).parameters
    assert "notify" not in parameters


def test_persist_candidate_record_stage_calls_add_item_without_notify_flag(
    process_manager: FileProcessManager,
    config_service,
    tmp_settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Persist candidate path should call add_item_to_record without notify kwarg."""
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
    expected_path = str(tmp_settings.DEST_DIR / "processed.txt")

    def add_item_to_record_without_notify(
        _record,
        src_path: str,
        filename_prefix: str,
        extension: str,
        file_processor,
        device=None,
    ) -> str:
        assert src_path == str(source)
        assert filename_prefix == "abc-ipat-sample"
        assert extension == ".txt"
        assert file_processor is candidate.processor
        assert device is candidate.device
        return expected_path

    monkeypatch.setattr(
        process_manager,
        "add_item_to_record",
        add_item_to_record_without_notify,
        raising=False,
    )

    result = process_manager._persist_candidate_record_stage(context)

    assert result == expected_path
