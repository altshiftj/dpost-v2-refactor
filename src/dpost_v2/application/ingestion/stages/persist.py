from __future__ import annotations

from typing import Any, Callable, Mapping

from dpost_v2.application.ingestion.runtime_services import RuntimeCallStatus
from dpost_v2.application.ingestion.stages.pipeline import (
    PipelineTerminalOutcome,
    StageDirective,
)
from dpost_v2.application.ingestion.state import IngestionState


def _status_token(result: Any) -> str:
    status = getattr(result, "status", RuntimeCallStatus.FAILED)
    if hasattr(status, "value"):
        return str(getattr(status, "value"))
    return str(status)


def _reason_code(result: Any, fallback: str) -> str:
    diagnostics = getattr(result, "diagnostics", {}) or {}
    return str(diagnostics.get("reason_code", fallback))


def run_persist_stage(
    state: IngestionState,
    *,
    move_file: Callable[[str, str], Any],
    save_record: Callable[[Mapping[str, Any]], Any],
    retry_planner: Callable[[str, int], Mapping[str, Any]],
) -> StageDirective[IngestionState]:
    """Persist routed candidate via file move and record-store mutation calls."""
    candidate = state.candidate
    if candidate is None or candidate.target_path is None:
        return StageDirective.terminal(PipelineTerminalOutcome.FAILED, state)

    move_result = move_file(candidate.source_path, candidate.target_path)
    if _status_token(move_result) != RuntimeCallStatus.SUCCESS.value:
        reason = _reason_code(move_result, "move_failed")
        plan = dict(retry_planner(reason, state.attempt_index))
        if plan.get("terminal_type") == "retry":
            retry_state = state.with_updates(
                retry_plan=plan,
                attempt_index=int(plan.get("next_attempt", state.attempt_index + 1)),
                diagnostics={"persist": {"reason_code": reason}},
            )
            return StageDirective.terminal(PipelineTerminalOutcome.RETRY, retry_state)
        if reason == "collision":
            rejected = state.with_updates(
                diagnostics={"persist": {"reason_code": reason}}
            )
            return StageDirective.terminal(PipelineTerminalOutcome.REJECTED, rejected)
        failed = state.with_updates(diagnostics={"persist": {"reason_code": reason}})
        return StageDirective.terminal(PipelineTerminalOutcome.FAILED, failed)

    record_payload = {
        "candidate": candidate.to_payload(),
        "target_path": candidate.target_path,
    }
    save_result = save_record(record_payload)
    if _status_token(save_result) != RuntimeCallStatus.SUCCESS.value:
        reason = _reason_code(save_result, "record_save_failed")
        plan = dict(retry_planner(reason, state.attempt_index))
        if plan.get("terminal_type") == "retry":
            retry_state = state.with_updates(
                retry_plan=plan,
                attempt_index=int(plan.get("next_attempt", state.attempt_index + 1)),
                diagnostics={"persist": {"reason_code": reason}},
            )
            return StageDirective.terminal(PipelineTerminalOutcome.RETRY, retry_state)
        failed = state.with_updates(diagnostics={"persist": {"reason_code": reason}})
        return StageDirective.terminal(PipelineTerminalOutcome.FAILED, failed)

    saved_value = getattr(save_result, "value", {}) or {}
    record_id = str(saved_value.get("record_id", "")).strip() or "unknown-record"
    persisted_candidate = candidate.with_persist_result(record_id, candidate.target_path)
    next_state = state.with_updates(
        candidate=persisted_candidate,
        record_id=record_id,
        diagnostics={"persist": {"reason_code": "persisted"}},
    )
    return StageDirective.continue_to("post_persist", next_state)
