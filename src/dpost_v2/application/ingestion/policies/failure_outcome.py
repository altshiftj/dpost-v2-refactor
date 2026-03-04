from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping


class FailureOutcomeError(ValueError):
    """Base failure-outcome normalization error."""


class FailureOutcomeTypeError(FailureOutcomeError):
    """Raised when terminal type and retry payload are inconsistent."""


class FailureTerminalType(StrEnum):
    """Canonical terminal types for normalized failures."""

    RETRY = "retry"
    FAILED = "failed"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class FailureOutcome:
    """Canonical failure outcome consumed by engine/emitter policies."""

    terminal_type: FailureTerminalType
    stage_id: str | None
    reason_code: str
    severity: str
    retry_plan: Mapping[str, Any] | None
    should_emit: bool


def build_failure_outcome(
    classification: Any,
    terminal_type: FailureTerminalType | None = None,
    retry_plan: Mapping[str, Any] | None = None,
    should_emit: bool = True,
) -> FailureOutcome:
    """Build and validate a canonical failure outcome from classification input."""
    resolved_terminal = terminal_type
    if resolved_terminal is None:
        resolved_terminal = (
            FailureTerminalType.RETRY
            if bool(getattr(classification, "retryable", False))
            else FailureTerminalType.FAILED
        )

    if resolved_terminal is FailureTerminalType.RETRY and retry_plan is None:
        raise FailureOutcomeTypeError(
            "Retry terminal type requires a retry plan payload."
        )
    if resolved_terminal is not FailureTerminalType.RETRY and retry_plan is not None:
        raise FailureOutcomeTypeError(
            "Non-retry terminal types must not include a retry plan payload."
        )

    return FailureOutcome(
        terminal_type=resolved_terminal,
        stage_id=getattr(classification, "stage_id", None),
        reason_code=str(getattr(classification, "reason_code", "unknown_error")),
        severity=str(getattr(classification, "severity", "error")),
        retry_plan=retry_plan,
        should_emit=should_emit,
    )
