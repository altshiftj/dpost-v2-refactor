"""Staging state machine and transition invariants for V2 domain."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class StagingModelError(ValueError):
    """Base class for staging state machine errors."""


class StagingStateUnknownError(StagingModelError):
    """Raised when a state token is not part of the finite state set."""


class StagingTransitionError(StagingModelError):
    """Raised when an event is illegal for the current state."""


class StagingReasonRequiredError(StagingModelError):
    """Raised when failure/reject transitions omit required reason code."""


class StagingAttemptOrderError(StagingModelError):
    """Raised when attempt index regresses across transitions."""


class StagingState(str, Enum):
    """Finite staging states for ingestion lifecycle."""

    OBSERVED = "observed"
    STABILIZED = "stabilized"
    ROUTED = "routed"
    PERSISTED = "persisted"
    FAILED = "failed"
    REJECTED = "rejected"


class StagingEvent(str, Enum):
    """Transition events that move staging state forward."""

    STABILIZED = "stabilized"
    ROUTED = "routed"
    PERSISTED = "persisted"
    FAILED = "failed"
    REJECTED = "rejected"


TERMINAL_STATES = frozenset(
    {
        StagingState.PERSISTED,
        StagingState.FAILED,
        StagingState.REJECTED,
    },
)

TRANSITIONS: dict[tuple[StagingState, StagingEvent], StagingState] = {
    (StagingState.OBSERVED, StagingEvent.STABILIZED): StagingState.STABILIZED,
    (StagingState.STABILIZED, StagingEvent.ROUTED): StagingState.ROUTED,
    (StagingState.ROUTED, StagingEvent.PERSISTED): StagingState.PERSISTED,
    (StagingState.OBSERVED, StagingEvent.FAILED): StagingState.FAILED,
    (StagingState.STABILIZED, StagingEvent.FAILED): StagingState.FAILED,
    (StagingState.ROUTED, StagingEvent.FAILED): StagingState.FAILED,
    (StagingState.OBSERVED, StagingEvent.REJECTED): StagingState.REJECTED,
    (StagingState.STABILIZED, StagingEvent.REJECTED): StagingState.REJECTED,
    (StagingState.ROUTED, StagingEvent.REJECTED): StagingState.REJECTED,
}


@dataclass(frozen=True)
class StagingTraceEntry:
    """Canonical trace entry for state transitions."""

    from_state: StagingState
    event: StagingEvent
    to_state: StagingState
    reason_code: str | None
    attempt_index: int | None


@dataclass(frozen=True)
class StagingTransitionResult:
    """Transition result with next state and trace diagnostics."""

    next_state: StagingState
    trace: StagingTraceEntry


def _coerce_state(state: StagingState | str) -> StagingState:
    if isinstance(state, StagingState):
        return state
    try:
        return StagingState(state)
    except ValueError as exc:
        raise StagingStateUnknownError(f"Unknown staging state '{state}'.") from exc


def _coerce_event(event: StagingEvent | str) -> StagingEvent:
    if isinstance(event, StagingEvent):
        return event
    try:
        return StagingEvent(event)
    except ValueError as exc:
        raise StagingTransitionError(f"Unknown staging event '{event}'.") from exc


def is_terminal_state(state: StagingState | str) -> bool:
    """Return whether the given state is terminal."""
    return _coerce_state(state) in TERMINAL_STATES


def transition_state(
    current_state: StagingState | str,
    event: StagingEvent | str,
    *,
    reason_code: str | None = None,
    attempt_index: int | None = None,
    previous_attempt_index: int | None = None,
) -> StagingTransitionResult:
    """Apply one state transition with invariant checks and trace output."""
    state = _coerce_state(current_state)
    resolved_event = _coerce_event(event)

    if state in TERMINAL_STATES:
        raise StagingTransitionError(
            f"Terminal state '{state.value}' has no outbound transitions.",
        )

    next_state = TRANSITIONS.get((state, resolved_event))
    if next_state is None:
        raise StagingTransitionError(
            f"Illegal staging transition ({state.value}, {resolved_event.value}).",
        )

    if (
        resolved_event in {StagingEvent.FAILED, StagingEvent.REJECTED}
        and not reason_code
    ):
        raise StagingReasonRequiredError(
            "Failure/reject transitions require reason_code.",
        )

    if (
        attempt_index is not None
        and previous_attempt_index is not None
        and attempt_index < previous_attempt_index
    ):
        raise StagingAttemptOrderError("attempt_index cannot regress.")

    trace = StagingTraceEntry(
        from_state=state,
        event=resolved_event,
        to_state=next_state,
        reason_code=reason_code,
        attempt_index=attempt_index,
    )
    return StagingTransitionResult(next_state=next_state, trace=trace)
