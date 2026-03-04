from __future__ import annotations

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


def test_persist_stage_continues_to_post_persist_on_success() -> None:
    state = IngestionState(event={}, candidate=_candidate())

    directive = run_persist_stage(
        state,
        move_file=lambda source, target: RuntimeCallResult(
            status=RuntimeCallStatus.SUCCESS,
            value=target,
            diagnostics={},
        ),
        save_record=lambda payload: RuntimeCallResult(
            status=RuntimeCallStatus.SUCCESS,
            value={"record_id": "r1"},
            diagnostics={},
        ),
        retry_planner=lambda reason, attempt: {"terminal_type": "stop_retrying"},
    )

    assert directive.kind == "continue"
    assert directive.next_stage == "post_persist"
    assert directive.state.record_id == "r1"


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


def test_post_persist_stage_completes_with_sync_warning_on_sync_failure() -> None:
    state = IngestionState(
        event={"event_id": "e1"}, candidate=_candidate(), record_id="r1"
    )

    directive = run_post_persist_stage(
        state,
        update_bookkeeping=lambda record_id, candidate: RuntimeCallResult(
            status=RuntimeCallStatus.SUCCESS,
            value=True,
            diagnostics={},
        ),
        trigger_sync=lambda record_id: RuntimeCallResult(
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
