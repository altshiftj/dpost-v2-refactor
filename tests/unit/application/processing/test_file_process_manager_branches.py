"""Focused branch coverage for file process manager orchestration paths."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, cast
from unittest.mock import MagicMock

import pytest

from dpost.application.interactions import DialogPrompts, ErrorMessages
from dpost.application.processing.device_resolver import DeviceResolution
from dpost.application.processing.failure_emitter import ProcessingFailureEmissionSink
from dpost.application.processing.failure_outcome_policy import (
    FailureMoveTarget,
    ProcessingFailureOutcome,
)
from dpost.application.processing.file_process_manager import FileProcessManager
from dpost.application.processing.file_processor_abstract import ProcessingOutput
from dpost.application.processing.rename_flow import RenameOutcome
from dpost.application.processing.stability_tracker import (
    FileStabilityTracker,
    StabilityOutcome,
)
from dpost.domain.processing.models import (
    ProcessingCandidate,
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
def manager_bundle(config_service, monkeypatch):
    """Create a process manager with stable-artefact checks defaulting to green."""
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


def _build_candidate(
    manager: FileProcessManager,
    *,
    path: Path,
    prefix: str,
    extension: str,
    device,
) -> ProcessingCandidate:
    """Create a minimal candidate for direct routing/pipeline branch tests."""
    return ProcessingCandidate(
        original_path=path,
        effective_path=path,
        prefix=prefix,
        extension=extension,
        processor=manager.file_processor,
        device=device,
        preprocessed_path=None,
    )


def test_process_item_defers_when_resolution_requests_retry(
    manager_bundle,
    config_service,
    tmp_settings,
    monkeypatch,
) -> None:
    """Return deferred result with retry delay when resolver asks for retry."""
    manager, _ = manager_bundle
    src = tmp_settings.WATCH_DIR / "abc-ipat-sample.txt"
    src.write_text("content")
    device = config_service.devices[0]

    monkeypatch.setattr(
        manager._device_resolver,
        "resolve",
        lambda _path: DeviceResolution.defer(
            reason=f"wait for {device.identifier}",
            retry_delay=4.25,
        ),
    )

    result = manager.process_item(str(src))

    assert result.status is ProcessingStatus.DEFERRED
    assert result.retry_delay == 4.25
    assert "wait for" in result.message


def test_process_item_defers_when_resolution_preselects_device_but_marks_deferred(
    manager_bundle,
    config_service,
    tmp_settings,
    monkeypatch,
) -> None:
    """Honor deferred resolver outcomes even when a candidate device is preselected."""
    manager, _ = manager_bundle
    src = tmp_settings.WATCH_DIR / "abc-ipat-sample.txt"
    src.write_text("content")
    device = config_service.devices[0]

    monkeypatch.setattr(
        manager._device_resolver,
        "resolve",
        lambda _path: DeviceResolution.defer(
            reason="waiting for reappearance",
            selected=device,
            retry_delay=2.0,
        ),
    )

    result = manager.process_item(str(src))

    assert result.status is ProcessingStatus.DEFERRED
    assert result.retry_delay == 2.0
    assert "reappearance" in result.message


def test_process_item_rejects_when_stability_guard_fails(
    manager_bundle,
    tmp_settings,
    monkeypatch,
) -> None:
    """Reject and queue item when stability tracker returns a rejected outcome."""
    manager, _ = manager_bundle
    src = tmp_settings.WATCH_DIR / "abc-ipat-sample.txt"
    src.write_text("content")

    monkeypatch.setattr(
        FileStabilityTracker,
        "wait",
        lambda self: StabilityOutcome(
            path=self.file_path,
            stable=False,
            reason="stability timeout",
        ),
    )

    moves: list[str] = []
    monkeypatch.setattr(
        "dpost.application.processing.file_process_manager.safe_move_to_exception",
        lambda path, *_args, **_kwargs: moves.append(path),
    )

    result = manager.process_item(str(src))

    assert result.status is ProcessingStatus.REJECTED
    assert result.message == "stability timeout"
    assert moves == [str(src)]
    assert manager.get_and_clear_rejected() == [(str(src), "stability timeout")]


def test_process_item_defers_when_path_missing_after_stability_guard_returns_stable(
    manager_bundle,
    config_service,
    tmp_settings,
    monkeypatch,
) -> None:
    """Defer when a path vanishes despite a stable outcome (race/over-optimistic stub)."""
    manager, _ = manager_bundle
    src = tmp_settings.WATCH_DIR / "abc-ipat-sample.txt"
    src.write_text("content")
    src.unlink()
    device = config_service.devices[0]

    monkeypatch.setattr(
        manager._device_resolver,
        "resolve",
        lambda _path: DeviceResolution.accept(device, reason="selected for test"),
    )

    monkeypatch.setattr(
        FileStabilityTracker,
        "wait",
        lambda self: StabilityOutcome(path=self.file_path, stable=True),
    )

    result = manager.process_item(str(src))

    assert result.status is ProcessingStatus.DEFERRED
    assert "disappeared before stability confirmation" in result.message


def test_persist_and_sync_stage_returns_processed_without_final_path(
    manager_bundle,
    config_service,
    tmp_settings,
    monkeypatch,
) -> None:
    """Treat missing final output path as processed with no path payload."""
    manager, _ = manager_bundle
    src = tmp_settings.WATCH_DIR / "abc-ipat-sample.txt"
    src.write_text("x")
    candidate = _build_candidate(
        manager,
        path=src,
        prefix="abc-ipat-sample",
        extension=".txt",
        device=config_service.devices[0],
    )
    context = RouteContext(candidate, "abc-ipat-sample", None, RoutingDecision.ACCEPT)
    monkeypatch.setattr(manager, "_persist_candidate_record_stage", lambda _ctx: None)

    result = manager._pipeline._persist_and_sync_stage(context)

    assert result.status is ProcessingStatus.PROCESSED
    assert result.final_path is None


def test_persist_and_sync_stage_returns_processed_with_final_path(
    manager_bundle,
    config_service,
    tmp_settings,
    monkeypatch,
) -> None:
    """Return processed result with path payload when persistence yields a final path."""
    manager, _ = manager_bundle
    src = tmp_settings.WATCH_DIR / "abc-ipat-sample.txt"
    src.write_text("x")
    candidate = _build_candidate(
        manager,
        path=src,
        prefix="abc-ipat-sample",
        extension=".txt",
        device=config_service.devices[0],
    )
    context = RouteContext(candidate, "abc-ipat-sample", None, RoutingDecision.ACCEPT)
    final_path = tmp_settings.WATCH_DIR / "records" / "abc-ipat-sample" / "item.txt"
    monkeypatch.setattr(
        manager,
        "_persist_candidate_record_stage",
        lambda _ctx: str(final_path),
    )

    result = manager._pipeline._persist_and_sync_stage(context)

    assert result.status is ProcessingStatus.PROCESSED
    assert result.final_path == final_path


def test_non_accept_route_stage_uses_record_flow_for_unappendable(
    manager_bundle,
    config_service,
    tmp_settings,
    monkeypatch,
) -> None:
    """Delegate unappendable outcomes to record flow with manager interactions."""
    manager, _ = manager_bundle
    src = tmp_settings.WATCH_DIR / "abc-ipat-sample.txt"
    src.write_text("x")
    candidate = _build_candidate(
        manager,
        path=src,
        prefix="abc-ipat-sample",
        extension=".txt",
        device=config_service.devices[0],
    )
    context = RouteContext(
        candidate,
        "abc-ipat-sample",
        None,
        RoutingDecision.UNAPPENDABLE,
    )
    expected = ProcessingResult(ProcessingStatus.REJECTED, "from-record-flow")
    captured: dict[str, object] = {}

    def fake_invoke(
        _candidate: ProcessingCandidate,
        prefix: str,
        extension: str,
        contextual_reason: str | None = None,
    ) -> ProcessingResult:
        captured["invoke"] = (prefix, extension, contextual_reason)
        return expected

    def fake_handle(
        interactions,
        rename_delegate: Callable[[str, str, str, str | None], ProcessingResult],
        received_context: RouteContext,
    ) -> ProcessingResult:
        captured["interactions"] = interactions
        captured["context"] = received_context
        return rename_delegate(
            str(received_context.candidate.effective_path),
            "retry-prefix",
            received_context.candidate.extension,
            "record blocked",
        )

    monkeypatch.setattr(manager._pipeline, "_invoke_rename_flow", fake_invoke)
    monkeypatch.setattr(
        "dpost.application.processing.file_process_manager.handle_unappendable_record",
        fake_handle,
    )

    result = manager._pipeline._non_accept_route_stage(context)

    assert result is expected
    assert captured["interactions"] is manager.interactions
    assert captured["context"] is context
    assert captured["invoke"] == ("retry-prefix", ".txt", "record blocked")


def test_non_accept_route_stage_rename_required_invokes_rename_flow(
    manager_bundle,
    config_service,
    tmp_settings,
    monkeypatch,
) -> None:
    """Route non-unappendable decisions directly through rename flow."""
    manager, _ = manager_bundle
    src = tmp_settings.WATCH_DIR / "badprefix.txt"
    src.write_text("x")
    candidate = _build_candidate(
        manager,
        path=src,
        prefix="badprefix",
        extension=".txt",
        device=config_service.devices[0],
    )
    context = RouteContext(candidate, "badprefix", None, RoutingDecision.REQUIRE_RENAME)
    expected = ProcessingResult(ProcessingStatus.REJECTED, "rename")
    calls: list[tuple[str, str, str | None]] = []

    def fake_invoke(
        _candidate: ProcessingCandidate,
        prefix: str,
        extension: str,
        contextual_reason: str | None = None,
    ) -> ProcessingResult:
        calls.append((prefix, extension, contextual_reason))
        return expected

    monkeypatch.setattr(manager._pipeline, "_invoke_rename_flow", fake_invoke)

    result = manager._pipeline._non_accept_route_stage(context)

    assert result is expected
    assert calls == [("badprefix", ".txt", None)]


def test_dispatch_route_delegates_by_routing_decision(
    manager_bundle,
    config_service,
    tmp_settings,
    monkeypatch,
) -> None:
    """Dispatch to accept/non-accept handlers according to route decision."""
    manager, _ = manager_bundle
    src = tmp_settings.WATCH_DIR / "dispatch.txt"
    src.write_text("x")
    candidate = _build_candidate(
        manager,
        path=src,
        prefix="dispatch",
        extension=".txt",
        device=config_service.devices[0],
    )
    accept_context = RouteContext(candidate, "dispatch", None, RoutingDecision.ACCEPT)
    rename_context = RouteContext(
        candidate,
        "dispatch",
        None,
        RoutingDecision.REQUIRE_RENAME,
    )
    accept_result = ProcessingResult(ProcessingStatus.PROCESSED, "accept")
    rename_result = ProcessingResult(ProcessingStatus.REJECTED, "rename")
    monkeypatch.setattr(
        manager._pipeline,
        "_persist_and_sync_stage",
        lambda _ctx: accept_result,
    )
    monkeypatch.setattr(
        manager._pipeline,
        "_non_accept_route_stage",
        lambda _ctx: rename_result,
    )

    assert manager._pipeline._dispatch_route(accept_context) is accept_result
    assert manager._pipeline._dispatch_route(rename_context) is rename_result


def test_invoke_rename_flow_retries_until_accept(
    manager_bundle,
    config_service,
    tmp_settings,
    monkeypatch,
) -> None:
    """Continue rename loop until routing transitions to ACCEPT."""
    manager, _ = manager_bundle
    src = tmp_settings.WATCH_DIR / "badprefix.txt"
    src.write_text("x")
    candidate = _build_candidate(
        manager,
        path=src,
        prefix="badprefix",
        extension=".txt",
        device=config_service.devices[0],
    )
    outcomes = iter(
        [
            RenameOutcome(sanitized_prefix="retry-one", cancelled=False),
            RenameOutcome(sanitized_prefix="retry-two", cancelled=False),
        ]
    )
    prompt_calls: list[tuple[str, str | None]] = []

    def fake_obtain(prefix: str, reason: str | None) -> RenameOutcome:
        prompt_calls.append((prefix, reason))
        return next(outcomes)

    def fake_route(updated: ProcessingCandidate) -> RouteContext:
        decision = (
            RoutingDecision.REQUIRE_RENAME
            if updated.prefix == "retry-one"
            else RoutingDecision.ACCEPT
        )
        return RouteContext(updated, updated.prefix, None, decision)

    monkeypatch.setattr(manager._rename_service, "obtain_valid_prefix", fake_obtain)
    monkeypatch.setattr(manager._pipeline, "_route_decision_stage", fake_route)
    monkeypatch.setattr(
        manager._pipeline,
        "_rename_retry_policy_stage",
        lambda _ctx: ("retry-two", "retry-context"),
    )
    monkeypatch.setattr(
        manager._pipeline,
        "_persist_and_sync_stage",
        lambda _ctx: ProcessingResult(ProcessingStatus.PROCESSED, "accepted"),
    )

    result = manager._pipeline._invoke_rename_flow(candidate, "initial", ".txt")

    assert result.status is ProcessingStatus.PROCESSED
    assert result.message == "accepted"
    assert prompt_calls == [("initial", None), ("retry-two", "retry-context")]


def test_rename_retry_policy_stage_unappendable_warns_with_context(
    manager_bundle,
    config_service,
    tmp_settings,
) -> None:
    """Warn and return contextual prompt details for unappendable record retries."""
    manager, ui = manager_bundle
    src = tmp_settings.WATCH_DIR / "abc-ipat-sample.txt"
    src.write_text("x")
    candidate = _build_candidate(
        manager,
        path=src,
        prefix="abc-ipat-sample",
        extension=".txt",
        device=config_service.devices[0],
    )
    context = RouteContext(
        candidate,
        "abc-ipat-sample",
        None,
        RoutingDecision.UNAPPENDABLE,
    )

    next_prefix, reason = manager._pipeline._rename_retry_policy_stage(context)

    assert next_prefix == "abc-ipat-sample"
    assert reason == DialogPrompts.UNAPPENDABLE_RECORD_CONTEXT.format(
        record_id="abc-ipat-sample"
    )
    assert ui.warnings


def test_rename_retry_policy_stage_default_returns_candidate_prefix(
    manager_bundle,
    config_service,
    tmp_settings,
) -> None:
    """Return candidate prefix with no contextual prompt for default retries."""
    manager, _ = manager_bundle
    src = tmp_settings.WATCH_DIR / "badprefix.txt"
    src.write_text("x")
    candidate = _build_candidate(
        manager,
        path=src,
        prefix="badprefix",
        extension=".txt",
        device=config_service.devices[0],
    )
    context = RouteContext(candidate, "badprefix", None, RoutingDecision.REQUIRE_RENAME)

    assert manager._pipeline._rename_retry_policy_stage(context) == ("badprefix", None)


def test_reject_immediately_defers_internal_staging_paths(
    manager_bundle,
    tmp_settings,
) -> None:
    """Treat internal staging artifacts as deferred instead of rejected."""
    manager, _ = manager_bundle
    staged = tmp_settings.WATCH_DIR / "sample.__staged__.txt"
    staged.write_text("x")

    result = manager._pipeline._reject_immediately(staged, "staged")

    assert result.status is ProcessingStatus.DEFERRED
    assert result.message == "staged"
    assert manager.get_and_clear_rejected() == [(str(staged), "staged")]


def test_resolve_record_processor_stage_raises_without_processor(
    manager_bundle,
    tmp_settings,
    monkeypatch,
) -> None:
    """Move source to exception flow and raise when no processor is available."""
    manager, _ = manager_bundle
    manager.file_processor = None
    src = tmp_settings.WATCH_DIR / "no-processor.txt"
    src.write_text("x")
    moved: list[str] = []
    monkeypatch.setattr(
        "dpost.application.processing.file_process_manager.move_to_exception_folder",
        lambda path: moved.append(path),
    )

    with pytest.raises(RuntimeError, match="No file processor available"):
        manager._resolve_record_processor_stage(None, str(src))

    assert moved == [str(src)]


def test_post_persist_side_effects_handles_force_path_variants(
    manager_bundle,
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Skip missing paths and mark all file targets unsynced for existing paths."""
    manager, _ = manager_bundle
    record_path = tmp_path / "record"
    record_path.mkdir()
    measurement = record_path / "measurement.csv"
    measurement.write_text("m")
    force_file = record_path / "force.csv"
    force_file.write_text("f")
    force_dir = record_path / "force-dir"
    nested = force_dir / "nested"
    nested.mkdir(parents=True)
    dir_file_one = force_dir / "a.csv"
    dir_file_two = nested / "b.csv"
    dir_file_one.write_text("a")
    dir_file_two.write_text("b")

    output = ProcessingOutput(
        final_path=str(measurement),
        datatype="dummy",
        force_paths=("", "missing.csv", "force.csv", "force-dir"),
    )
    update_calls: list[str] = []

    def fake_update(_records, path: str, _record) -> int:
        update_calls.append(path)
        return 1

    monkeypatch.setattr(
        "dpost.application.processing.file_process_manager.update_record",
        fake_update,
    )
    record = MagicMock()

    manager._post_persist_side_effects_stage(
        output,
        record,
        str(record_path),
        str(measurement),
    )

    assert update_calls == [
        str(measurement),
        str(force_file),
        str(force_dir),
    ]
    marked = {call.args[0] for call in record.mark_file_as_unsynced.call_args_list}
    assert marked == {str(force_file), str(dir_file_one), str(dir_file_two)}


def test_post_persist_side_effects_reports_immediate_sync_error(
    config_service,
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Show sync error details when immediate sync fails after processing."""
    ui = HeadlessUI()
    sync = DummySyncManager(ui)
    session = FakeSessionManager(interactions=ui, scheduler=ui)
    manager = FileProcessManager(
        interactions=ui,
        sync_manager=sync,
        session_manager=session,
        config_service=config_service,
        file_processor=DummyProcessor(),
        immediate_sync=True,
    )
    measurement = tmp_path / "item.csv"
    measurement.write_text("x")
    output = ProcessingOutput(final_path=str(measurement), datatype="dummy")

    monkeypatch.setattr(
        "dpost.application.processing.file_process_manager.update_record",
        lambda _records, _path, _record: 1,
    )
    monkeypatch.setattr(manager.records, "all_records_uploaded", lambda: False)
    monkeypatch.setattr(
        manager.records,
        "sync_records_to_database",
        lambda: (_ for _ in ()).throw(RuntimeError("sync boom")),
    )

    manager._post_persist_side_effects_stage(
        output,
        MagicMock(),
        str(tmp_path),
        str(measurement),
    )

    assert ui.errors
    title, message = ui.errors[-1]
    assert title == ErrorMessages.SYNC_ERROR
    assert "sync boom" in message


def test_sync_records_to_database_respects_upload_state(
    manager_bundle,
    monkeypatch,
) -> None:
    """Skip sync when uploaded and call sync when pending uploads remain."""
    manager, _ = manager_bundle
    calls = {"count": 0}
    monkeypatch.setattr(
        manager.records,
        "sync_records_to_database",
        lambda: calls.__setitem__("count", calls["count"] + 1),
    )

    monkeypatch.setattr(manager.records, "all_records_uploaded", lambda: True)
    manager.sync_records_to_database()
    assert calls["count"] == 0

    monkeypatch.setattr(manager.records, "all_records_uploaded", lambda: False)
    manager.sync_records_to_database()
    assert calls["count"] == 1


def test_resolve_processor_uses_factory_when_instance_processor_missing(
    manager_bundle,
    config_service,
    monkeypatch,
) -> None:
    """Defer processor resolution to factory when manager has no static processor."""
    manager, _ = manager_bundle
    manager.file_processor = None
    fallback = DummyProcessor()
    calls: list[str] = []
    monkeypatch.setattr(
        manager._processor_factory,
        "get_for_device",
        lambda identifier: calls.append(identifier) or fallback,
    )

    resolved = manager._resolve_processor(config_service.devices[0])

    assert resolved is fallback
    assert calls == [config_service.devices[0].identifier]


def test_strip_internal_stage_suffix_removes_countered_suffix() -> None:
    """Strip internal staged marker from filenames while preserving extension."""
    source = Path("C:/tmp/sample.__staged__3.csv")
    stripped = FileProcessManager._strip_internal_stage_suffix(source)
    assert stripped.name == "sample.csv"


def test_handle_processing_failure_moves_preprocessed_artifact_when_distinct(
    manager_bundle,
    config_service,
    tmp_settings,
) -> None:
    """Move both effective and preprocessed paths when they differ on failure."""
    manager, _ = manager_bundle
    src = tmp_settings.WATCH_DIR / "abc-ipat-sample.txt"
    prepared = tmp_settings.WATCH_DIR / "abc-ipat-sample.__staged__.txt"
    src.write_text("raw")
    prepared.write_text("prepared")
    candidate = ProcessingCandidate(
        original_path=src,
        effective_path=src,
        prefix="abc-ipat-sample",
        extension=".txt",
        processor=manager.file_processor,
        device=config_service.devices[0],
        preprocessed_path=prepared,
    )
    moves: list[tuple[str, str | None, str | None]] = []
    manager._failure_emission_sink = ProcessingFailureEmissionSink(
        log_exception=lambda *_args, **_kwargs: None,
        move_to_exception=lambda path, prefix, extension: moves.append(
            (path, prefix, extension)
        ),
        register_rejection=lambda *_args, **_kwargs: None,
        increment_failed_metric=lambda: None,
    )

    manager._handle_processing_failure(src, candidate, RuntimeError("boom"))

    assert moves == [
        (str(src), "abc-ipat-sample", ".txt"),
        (str(prepared), "abc-ipat-sample", ".txt"),
    ]


def test_emit_processing_failure_outcome_stage_emits_log_moves_rejection_and_metric(
    manager_bundle,
) -> None:
    """Delegate failure side effects through the injected emission sink."""
    manager, _ = manager_bundle
    src = Path("C:/watch/failure.txt")
    exc = RuntimeError("boom")
    outcome = ProcessingFailureOutcome(
        move_targets=(
            FailureMoveTarget(
                path="C:/watch/failure.txt",
                prefix="failure",
                extension=".txt",
            ),
        ),
        rejection_path="C:/watch/failure.txt",
        rejection_reason="boom",
    )
    captured: dict[str, object] = {}
    manager._failure_emission_sink = ProcessingFailureEmissionSink(
        log_exception=lambda logged_path, logged_exc: captured.__setitem__(
            "log", (logged_path, logged_exc)
        ),
        move_to_exception=lambda path, prefix, extension: cast(
            list[tuple[str, str, str]],
            captured.setdefault("moves", []),
        ).append((path, prefix, extension)),
        register_rejection=lambda path, reason: captured.__setitem__(
            "rejection", (path, reason)
        ),
        increment_failed_metric=lambda: captured.__setitem__("metric_called", True),
    )

    manager._emit_processing_failure_outcome_stage(src, exc, outcome)

    assert captured["log"] == (src, exc)
    assert captured["moves"] == [("C:/watch/failure.txt", "failure", ".txt")]
    assert captured["rejection"] == ("C:/watch/failure.txt", "boom")
    assert captured["metric_called"] is True


def test_log_processing_failure_exception_logs_with_path_and_exception(
    monkeypatch,
) -> None:
    """Format failure exception logs with path and exception context."""
    logger_mock = MagicMock()
    src = Path("C:/watch/failure.txt")
    exc = RuntimeError("boom")
    monkeypatch.setattr(
        "dpost.application.processing.file_process_manager.logger",
        logger_mock,
    )

    FileProcessManager._log_processing_failure_exception(src, exc)

    logger_mock.exception.assert_called_once_with("Error processing %s: %s", src, exc)


def test_init_triggers_startup_sync_when_records_pending(
    config_service,
    monkeypatch,
) -> None:
    """Run startup sync branch when record manager reports pending uploads."""
    ui = HeadlessUI()
    sync = DummySyncManager(ui)
    session = FakeSessionManager(interactions=ui, scheduler=ui)
    sync_calls = {"count": 0}
    monkeypatch.setattr(
        "dpost.application.processing.file_process_manager.RecordManager.all_records_uploaded",
        lambda self: False,
    )
    monkeypatch.setattr(
        "dpost.application.processing.file_process_manager.RecordManager.sync_records_to_database",
        lambda self: sync_calls.__setitem__("count", sync_calls["count"] + 1),
    )

    FileProcessManager(
        interactions=ui,
        sync_manager=sync,
        session_manager=session,
        config_service=config_service,
        file_processor=DummyProcessor(),
    )

    assert sync_calls["count"] == 1


def test_should_queue_modified_delegates_to_modified_event_gate(
    manager_bundle,
    monkeypatch,
) -> None:
    """Expose modified-event gate decision through manager facade."""
    manager, _ = manager_bundle
    monkeypatch.setattr(manager._modified_event_gate, "should_queue", lambda _p: True)

    assert manager.should_queue_modified("C:/watch/file.csv") is True
