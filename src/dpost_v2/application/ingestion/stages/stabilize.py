from __future__ import annotations

from typing import Any, Callable

from dpost_v2.application.ingestion.policies.modified_event_gate import (
    ModifiedEventDecision,
)
from dpost_v2.application.ingestion.stages.pipeline import (
    PipelineTerminalOutcome,
    StageDirective,
)
from dpost_v2.application.ingestion.state import IngestionState


class StabilizePolicyConfigurationError(ValueError):
    """Raised when stabilize-stage settle policy is invalid."""


def _decision_token(decision: Any) -> str:
    if hasattr(decision, "value"):
        return str(getattr(decision, "value"))
    return str(decision)


def run_stabilize_stage(
    state: IngestionState,
    *,
    modified_event_gate: Callable[[str, float], Any],
    now_provider: Callable[[], float],
    settle_delay_seconds: float,
) -> StageDirective[IngestionState]:
    """Apply duplicate-event and settle-delay policy before routing stages."""
    if settle_delay_seconds < 0:
        raise StabilizePolicyConfigurationError(
            "settle_delay_seconds must be non-negative."
        )
    candidate = state.candidate
    if candidate is None:
        return StageDirective.terminal(PipelineTerminalOutcome.FAILED, state)

    now_value = float(now_provider())
    gate_result = modified_event_gate(candidate.identity_token, now_value)
    decision = _decision_token(
        getattr(gate_result, "decision", ModifiedEventDecision.ALLOW)
    )

    if decision == ModifiedEventDecision.DROP_DUPLICATE.value:
        rejected = state.with_updates(
            diagnostics={"stabilize": {"reason_code": "duplicate_event"}}
        )
        return StageDirective.terminal(PipelineTerminalOutcome.REJECTED, rejected)
    if decision in {ModifiedEventDecision.DEFER.value, "defer_retry"}:
        retry_state = state.with_updates(
            diagnostics={"stabilize": {"reason_code": "gate_deferred"}}
        )
        return StageDirective.terminal(PipelineTerminalOutcome.RETRY, retry_state)

    if candidate.modified_at is None:
        failed = state.with_updates(
            diagnostics={"stabilize": {"reason_code": "missing_modified_timestamp"}}
        )
        return StageDirective.terminal(PipelineTerminalOutcome.FAILED, failed)
    if now_value < candidate.modified_at:
        failed = state.with_updates(
            diagnostics={"stabilize": {"reason_code": "clock_regression"}}
        )
        return StageDirective.terminal(PipelineTerminalOutcome.FAILED, failed)

    age = now_value - candidate.modified_at
    if age < settle_delay_seconds:
        retry_state = state.with_updates(
            diagnostics={
                "stabilize": {
                    "reason_code": "settle_delay_not_elapsed",
                    "age_seconds": age,
                    "required_seconds": settle_delay_seconds,
                }
            }
        )
        return StageDirective.terminal(PipelineTerminalOutcome.RETRY, retry_state)

    ready_state = state.with_updates(
        diagnostics={"stabilize": {"reason_code": "ready"}}
    )
    return StageDirective.continue_to("route", ready_state)
