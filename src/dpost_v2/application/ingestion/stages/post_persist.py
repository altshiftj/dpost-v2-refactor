from __future__ import annotations

from typing import Any, Callable

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


def run_post_persist_stage(
    state: IngestionState,
    *,
    update_bookkeeping: Callable[[str, Any], Any],
    trigger_sync: Callable[[str], Any],
    emit_sync_error: Callable[[str, str, str], None],
    immediate_sync_enabled: bool,
) -> StageDirective[IngestionState]:
    """Apply post-persist bookkeeping and optional immediate-sync behaviors."""
    if state.candidate is None or state.record_id is None:
        return StageDirective.terminal(PipelineTerminalOutcome.FAILED, state)

    bookkeeping_result = update_bookkeeping(state.record_id, state.candidate)
    if _status_token(bookkeeping_result) != RuntimeCallStatus.SUCCESS.value:
        failed = state.with_updates(
            diagnostics={"post_persist": {"reason_code": "bookkeeping_failed"}}
        )
        return StageDirective.terminal(PipelineTerminalOutcome.FAILED, failed)

    if immediate_sync_enabled:
        sync_result = trigger_sync(state.record_id)
        if _status_token(sync_result) != RuntimeCallStatus.SUCCESS.value:
            diagnostics = getattr(sync_result, "diagnostics", {}) or {}
            reason_code = str(diagnostics.get("reason_code", "sync_failed"))
            emit_sync_error(
                str(state.event.get("event_id", state.correlation_id or "")),
                state.record_id,
                reason_code,
            )
            warning_state = state.with_updates(
                sync_warning=reason_code,
                diagnostics={"post_persist": {"reason_code": "sync_warning"}},
            )
            return StageDirective.terminal(PipelineTerminalOutcome.COMPLETED, warning_state)

    completed = state.with_updates(
        diagnostics={"post_persist": {"reason_code": "completed"}}
    )
    return StageDirective.terminal(PipelineTerminalOutcome.COMPLETED, completed)
