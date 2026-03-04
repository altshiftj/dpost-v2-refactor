from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import json
from typing import Any, Callable, Mapping


class EmissionStatus(StrEnum):
    """Failure emission terminal statuses."""

    EMITTED = "emitted"
    SUPPRESSED = "suppressed"
    EMIT_FAILED = "emit_failed"


@dataclass(frozen=True, slots=True)
class EmissionResult:
    """Result payload for one failure emission attempt."""

    status: EmissionStatus
    payload: Mapping[str, Any]
    diagnostics: Mapping[str, Any] = field(default_factory=dict)


def emit_failure_event(
    *,
    failure_outcome: Any,
    correlation_context: Mapping[str, Any],
    event_port: Callable[[dict[str, Any]], None],
    suppress: bool = False,
) -> EmissionResult:
    """Emit one normalized failure payload to an event sink with suppression support."""
    payload: dict[str, Any] = {
        "event_id": correlation_context.get("event_id"),
        "stage_id": getattr(failure_outcome, "stage_id", None),
        "reason_code": getattr(failure_outcome, "reason_code", "unknown_error"),
        "severity": getattr(failure_outcome, "severity", "error"),
        "terminal_type": str(getattr(failure_outcome, "terminal_type", "failed")),
        "retry_plan": getattr(failure_outcome, "retry_plan", None),
    }

    try:
        json.dumps(payload, sort_keys=True)
    except TypeError as exc:
        return EmissionResult(
            status=EmissionStatus.EMIT_FAILED,
            payload=payload,
            diagnostics={"reason": "serialization_error", "message": str(exc)},
        )

    if suppress:
        return EmissionResult(
            status=EmissionStatus.SUPPRESSED,
            payload=payload,
            diagnostics={"reason": "suppressed_by_policy"},
        )

    try:
        event_port(payload)
    except Exception as exc:  # noqa: BLE001
        return EmissionResult(
            status=EmissionStatus.EMIT_FAILED,
            payload=payload,
            diagnostics={"reason": "adapter_error", "message": str(exc)},
        )

    return EmissionResult(status=EmissionStatus.EMITTED, payload=payload)
