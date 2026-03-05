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
    diagnostics = _diagnostics(result)
    return str(diagnostics.get("reason_code", fallback))


def _diagnostics(result: Any) -> Mapping[str, Any]:
    diagnostics = getattr(result, "diagnostics", {}) or {}
    if isinstance(diagnostics, Mapping):
        return diagnostics
    return {}


def _normalized_retry_plan(
    raw_plan: Any,
    *,
    attempt_index: int,
) -> dict[str, Any] | None:
    if not isinstance(raw_plan, Mapping):
        return None
    plan = dict(raw_plan)
    terminal_type = str(plan.get("terminal_type", "")).strip().lower()
    if terminal_type != "retry":
        return plan

    try:
        next_attempt = int(plan.get("next_attempt", attempt_index + 1))
        delay_seconds = float(plan.get("delay_seconds", 0.0))
    except (TypeError, ValueError):
        return None

    if next_attempt <= attempt_index:
        next_attempt = attempt_index + 1
    if delay_seconds < 0:
        delay_seconds = 0.0

    plan["terminal_type"] = "retry"
    plan["next_attempt"] = next_attempt
    plan["delay_seconds"] = round(delay_seconds, 6)
    return plan


def _retry_or_terminal_for_failure(
    state: IngestionState,
    *,
    reason: str,
    retry_planner: Callable[[str, int], Mapping[str, Any]],
) -> StageDirective[IngestionState] | None:
    try:
        raw_plan = retry_planner(reason, state.attempt_index)
    except Exception:  # noqa: BLE001
        failed = state.with_updates(
            diagnostics={"persist": {"reason_code": "invalid_retry_plan"}}
        )
        return StageDirective.terminal(PipelineTerminalOutcome.FAILED, failed)

    plan = _normalized_retry_plan(raw_plan, attempt_index=state.attempt_index)
    if plan is None:
        failed = state.with_updates(
            diagnostics={"persist": {"reason_code": "invalid_retry_plan"}}
        )
        return StageDirective.terminal(PipelineTerminalOutcome.FAILED, failed)

    if plan.get("terminal_type") != "retry":
        return None

    retry_state = state.with_updates(
        retry_plan=plan,
        attempt_index=int(plan.get("next_attempt", state.attempt_index + 1)),
        diagnostics={"persist": {"reason_code": reason}},
    )
    return StageDirective.terminal(PipelineTerminalOutcome.RETRY, retry_state)


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
        retry_directive = _retry_or_terminal_for_failure(
            state,
            reason=reason,
            retry_planner=retry_planner,
        )
        if retry_directive is not None:
            return retry_directive
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
        retry_directive = _retry_or_terminal_for_failure(
            state,
            reason=reason,
            retry_planner=retry_planner,
        )
        if retry_directive is not None:
            return retry_directive
        failed = state.with_updates(diagnostics={"persist": {"reason_code": reason}})
        return StageDirective.terminal(PipelineTerminalOutcome.FAILED, failed)

    saved_value = getattr(save_result, "value", {}) or {}
    record_id = str(saved_value.get("record_id", "")).strip() or "unknown-record"
    persisted_candidate = candidate.with_persist_result(
        record_id, candidate.target_path
    )
    next_state = state.with_updates(
        candidate=persisted_candidate,
        record_id=record_id,
        diagnostics={"persist": {"reason_code": "persisted"}},
    )
    return StageDirective.continue_to("post_persist", next_state)
