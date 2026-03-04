from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from dpost_v2.application.ingestion.policies.failure_emitter import (
    EmissionResult,
    EmissionStatus,
    emit_failure_event,
)
from dpost_v2.application.ingestion.policies.failure_outcome import (
    FailureTerminalType,
    build_failure_outcome,
)


_EMITTED_EVENT_IDS: set[str] = set()


@dataclass(frozen=True, slots=True)
class ImmediateSyncEmissionPackage:
    """Immediate-sync failure normalization and emission result bundle."""

    failure_outcome: Any
    emission_result: EmissionResult
    mark_unsynced: bool
    escalation: bool


def emit_immediate_sync_failure(
    *,
    event_id: str,
    record_id: str,
    error: Exception,
    event_port: Callable[[dict[str, object]], None],
) -> ImmediateSyncEmissionPackage:
    """Emit immediate-sync failures once per event id with deterministic payload."""
    classification = type(
        "ImmediateSyncClassification",
        (),
        {
            "stage_id": "post_persist",
            "reason_code": "immediate_sync_error",
            "severity": "warning",
            "retryable": False,
        },
    )()
    outcome = build_failure_outcome(
        classification=classification,
        terminal_type=FailureTerminalType.FAILED,
    )

    if event_id in _EMITTED_EVENT_IDS:
        result = EmissionResult(
            status=EmissionStatus.SUPPRESSED,
            payload={
                "event_id": event_id,
                "record_id": record_id,
                "reason": str(error),
            },
            diagnostics={"reason": "already_emitted_for_event"},
        )
        return ImmediateSyncEmissionPackage(
            failure_outcome=outcome,
            emission_result=result,
            mark_unsynced=True,
            escalation=False,
        )

    result = emit_failure_event(
        failure_outcome=outcome,
        correlation_context={
            "event_id": event_id,
            "record_id": record_id,
            "sync_error": str(error),
        },
        event_port=event_port,
    )
    if result.status is EmissionStatus.EMITTED:
        _EMITTED_EVENT_IDS.add(event_id)

    return ImmediateSyncEmissionPackage(
        failure_outcome=outcome,
        emission_result=result,
        mark_unsynced=True,
        escalation=result.status is EmissionStatus.EMIT_FAILED,
    )
