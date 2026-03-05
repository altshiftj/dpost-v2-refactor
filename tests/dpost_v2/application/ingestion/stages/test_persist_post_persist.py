from __future__ import annotations

from datetime import UTC, datetime

from dpost_v2.application.contracts.context import ProcessingContext, RuntimeContext
from dpost_v2.application.contracts.plugin_contracts import ProcessorResult
from dpost_v2.application.ingestion.models.candidate import Candidate
from dpost_v2.application.ingestion.runtime_services import (
    RuntimeCallResult,
    RuntimeCallStatus,
)
from dpost_v2.application.ingestion.stages.persist import run_persist_stage
from dpost_v2.application.ingestion.stages.pipeline import PipelineTerminalOutcome
from dpost_v2.application.ingestion.stages.post_persist import run_post_persist_stage
from dpost_v2.application.ingestion.state import IngestionState


def _candidate() -> Candidate:
    return (
        Candidate.from_event(
            {
                "path": "incoming/file.txt",
                "event_kind": "created",
                "observed_at": 100.0,
            },
            {"modified_at": 90.0},
        )
        .with_resolution("plug", "proc")
        .with_route("C:/dest/out.txt", {"rule": "default"})
    )


def _processing_context() -> ProcessingContext:
    runtime_context = RuntimeContext.from_settings(
        settings={
            "mode": "headless",
            "profile": "prod",
            "session_id": "session-post-persist",
            "event_id": "event-post-persist",
            "trace_id": "trace-post-persist",
        },
        dependency_ids={"clock": "clock-1", "ui": "ui-1", "sync": "sync-1"},
    )
    return ProcessingContext.for_candidate(
        runtime_context=runtime_context,
        candidate_event={
            "source_path": "incoming/file.txt",
            "event_type": "created",
            "observed_at": datetime(2026, 3, 5, 12, 0, tzinfo=UTC),
            "event_id": "event-post-persist",
            "trace_id": "trace-post-persist",
        },
    )


def test_persist_stage_continues_to_post_persist_on_success() -> None:
    captured_payload: list[dict[str, object]] = []
    state = IngestionState(
        event={},
        candidate=_candidate(),
        processor_result=ProcessorResult(
            final_path="D:/normalized/out.txt",
            datatype="plug/output",
        ),
    )

    directive = run_persist_stage(
        state,
        move_file=lambda source, target: RuntimeCallResult(
            status=RuntimeCallStatus.SUCCESS,
            value=target,
            diagnostics={},
        ),
        save_record=lambda payload: captured_payload.append(dict(payload))
        or RuntimeCallResult(
            status=RuntimeCallStatus.SUCCESS,
            value={
                "record_id": "r1",
                "revision": 1,
                "record_snapshot": {
                    "record_id": "r1",
                    "revision": 1,
                    "payload": {
                        "candidate": _candidate().to_payload(),
                        "processor_result": {
                            "final_path": "D:/normalized/out.txt",
                            "datatype": "plug/output",
                            "force_paths": (),
                        },
                        "target_path": "C:/dest/out.txt",
                    },
                },
            },
            diagnostics={},
        ),
        retry_planner=lambda reason, attempt: {"terminal_type": "stop_retrying"},
    )

    assert directive.kind == "continue"
    assert directive.next_stage == "post_persist"
    assert directive.state.record_id == "r1"
    assert directive.state.record_snapshot == {
        "record_id": "r1",
        "revision": 1,
        "payload": {
            "candidate": _candidate().to_payload(),
            "processor_result": {
                "final_path": "D:/normalized/out.txt",
                "datatype": "plug/output",
                "force_paths": (),
            },
            "target_path": "C:/dest/out.txt",
        },
    }
    assert captured_payload == [
        {
            "candidate": _candidate().to_payload(),
            "processor_result": {
                "final_path": "D:/normalized/out.txt",
                "datatype": "plug/output",
                "force_paths": (),
            },
            "target_path": "C:/dest/out.txt",
        }
    ]


def test_persist_stage_returns_retry_when_move_fails_with_retry_plan() -> None:
    state = IngestionState(event={}, candidate=_candidate(), attempt_index=1)

    directive = run_persist_stage(
        state,
        move_file=lambda source, target: RuntimeCallResult(
            status=RuntimeCallStatus.FAILED,
            value=None,
            diagnostics={"reason_code": "file_locked"},
        ),
        save_record=lambda payload: RuntimeCallResult(
            status=RuntimeCallStatus.SUCCESS,
            value={"record_id": "r1"},
            diagnostics={},
        ),
        retry_planner=lambda reason, attempt: {
            "terminal_type": "retry",
            "delay_seconds": 3.0,
            "next_attempt": attempt + 1,
        },
    )

    assert directive.kind == "terminal"
    assert directive.outcome is PipelineTerminalOutcome.RETRY


def test_persist_stage_fails_when_retry_plan_is_malformed() -> None:
    state = IngestionState(event={}, candidate=_candidate(), attempt_index=1)

    directive = run_persist_stage(
        state,
        move_file=lambda source, target: RuntimeCallResult(
            status=RuntimeCallStatus.FAILED,
            value=None,
            diagnostics={"reason_code": "file_locked"},
        ),
        save_record=lambda payload: RuntimeCallResult(
            status=RuntimeCallStatus.SUCCESS,
            value={"record_id": "r1"},
            diagnostics={},
        ),
        retry_planner=lambda reason, attempt: {
            "terminal_type": "retry",
            "next_attempt": "not-a-number",
        },
    )

    assert directive.kind == "terminal"
    assert directive.outcome is PipelineTerminalOutcome.FAILED
    assert directive.state.diagnostics["persist"]["reason_code"] == "invalid_retry_plan"


def test_post_persist_stage_completes_with_sync_warning_on_sync_failure() -> None:
    state = IngestionState(
        event={"event_id": "e1"},
        candidate=_candidate(),
        record_id="r1",
        record_snapshot={
            "record_id": "r1",
            "payload": {"target_path": "C:/dest/out.txt"},
        },
        processing_context=_processing_context(),
    )

    directive = run_post_persist_stage(
        state,
        update_bookkeeping=lambda record_id, candidate: RuntimeCallResult(
            status=RuntimeCallStatus.SUCCESS,
            value=True,
            diagnostics={},
        ),
        trigger_sync=lambda sync_state: RuntimeCallResult(
            status=RuntimeCallStatus.FAILED,
            value=None,
            diagnostics={"reason_code": "sync_offline"},
        ),
        emit_sync_error=lambda event_id, record_id, reason: None,
        immediate_sync_enabled=True,
    )

    assert directive.kind == "terminal"
    assert directive.outcome is PipelineTerminalOutcome.COMPLETED
    assert directive.state.sync_warning == "sync_offline"


def test_post_persist_stage_uses_fallback_sync_reason_for_malformed_diagnostics() -> (
    None
):
    emitted: list[tuple[str, str, str]] = []
    triggered_states: list[IngestionState] = []
    state = IngestionState(
        event={"event_id": "e1"},
        candidate=_candidate(),
        record_id="r1",
        record_snapshot={
            "record_id": "r1",
            "payload": {"target_path": "C:/dest/out.txt"},
        },
        processing_context=_processing_context(),
    )

    directive = run_post_persist_stage(
        state,
        update_bookkeeping=lambda record_id, candidate: RuntimeCallResult(
            status=RuntimeCallStatus.SUCCESS,
            value=True,
            diagnostics={},
        ),
        trigger_sync=lambda sync_state: triggered_states.append(sync_state)
        or RuntimeCallResult(
            status=RuntimeCallStatus.FAILED,
            value=None,
            diagnostics=["not", "a", "mapping"],
        ),
        emit_sync_error=lambda event_id, record_id, reason: emitted.append(
            (event_id, record_id, reason)
        ),
        immediate_sync_enabled=True,
    )

    assert directive.kind == "terminal"
    assert directive.outcome is PipelineTerminalOutcome.COMPLETED
    assert directive.state.sync_warning == "sync_failed"
    assert emitted == [("e1", "r1", "sync_failed")]
    assert triggered_states[0].record_snapshot == {
        "record_id": "r1",
        "payload": {"target_path": "C:/dest/out.txt"},
    }
