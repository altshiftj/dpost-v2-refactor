"""Session lifecycle state machine used by V2 runtime orchestration."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from typing import Callable, Protocol, Sequence


class SessionError(RuntimeError):
    """Base error for session manager behavior."""


class SessionTransitionError(SessionError):
    """Raised when requested session state transition is invalid."""


class SessionNotStartedError(SessionError):
    """Raised when activity/stop/abort operations run before start."""


class SessionTimeSourceError(SessionError):
    """Raised when provided timestamps violate monotonic ordering."""


class SessionStateKind(StrEnum):
    """Explicit session lifecycle states."""

    INACTIVE = "inactive"
    STARTING = "starting"
    ACTIVE = "active"
    STOPPING = "stopping"
    ABORTED = "aborted"
    COMPLETED = "completed"


class TimeoutOutcome(StrEnum):
    """Timeout classification outcomes used by runtime loop decisions."""

    STILL_ACTIVE = "still_active"
    SOFT_TIMEOUT = "soft_timeout"
    HARD_TIMEOUT = "hard_timeout"
    NOT_STARTED = "not_started"


@dataclass(frozen=True, slots=True)
class SessionPolicy:
    """Session timeout policy configuration."""

    idle_timeout_seconds: float | None = None
    max_runtime_seconds: float | None = None

    def __post_init__(self) -> None:
        if self.idle_timeout_seconds is not None and self.idle_timeout_seconds < 0:
            raise ValueError("idle_timeout_seconds must be non-negative when provided")
        if self.max_runtime_seconds is not None and self.max_runtime_seconds < 0:
            raise ValueError("max_runtime_seconds must be non-negative when provided")


@dataclass(frozen=True, slots=True)
class SessionState:
    """Immutable snapshot of current session lifecycle state."""

    kind: SessionStateKind
    session_id: str | None = None
    started_at: datetime | None = None
    last_activity_at: datetime | None = None
    ended_at: datetime | None = None
    reason_code: str | None = None


@dataclass(frozen=True, slots=True)
class SessionTransitionResult:
    """Transition result including optional callback warnings."""

    previous_state: SessionState
    next_state: SessionState
    reason_code: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TimeoutEvaluation:
    """Current timeout posture for active session management."""

    outcome: TimeoutOutcome
    idle_elapsed_seconds: float
    runtime_elapsed_seconds: float


class ClockPort(Protocol):
    """Clock interface used by session manager for deterministic tests."""

    def now(self) -> datetime:
        """Return current time in session clock domain."""


@dataclass(frozen=True, slots=True)
class SessionSummary:
    """Structured session state summary for diagnostics."""

    state_kind: SessionStateKind
    session_id: str | None
    started_at: datetime | None
    last_activity_at: datetime | None
    ended_at: datetime | None


class SessionManager:
    """Lifecycle manager implementing explicit transition and timeout logic."""

    def __init__(
        self,
        *,
        policy: SessionPolicy,
        clock: ClockPort,
        transition_callbacks: Sequence[Callable[[SessionTransitionResult], None]] = (),
    ) -> None:
        self._policy = policy
        self._clock = clock
        self._transition_callbacks = tuple(transition_callbacks)
        self._state = SessionState(kind=SessionStateKind.INACTIVE)

    @property
    def state(self) -> SessionState:
        """Return current immutable session state."""
        return self._state

    def start_session(
        self,
        *,
        session_id: str,
        started_at: datetime | None = None,
    ) -> SessionTransitionResult:
        """Start a session or return idempotent result for identical active session."""
        normalized_id = _normalize_session_id(session_id)
        previous = self._state

        if previous.kind is SessionStateKind.ACTIVE:
            if previous.session_id == normalized_id:
                return SessionTransitionResult(
                    previous_state=previous,
                    next_state=previous,
                    reason_code="idempotent_start",
                )
            raise SessionTransitionError(
                f"Cannot start {normalized_id!r}; active session {previous.session_id!r} exists."
            )
        if previous.kind is not SessionStateKind.INACTIVE:
            raise SessionTransitionError(
                f"Cannot start from state {previous.kind.value!r}."
            )

        event_time = self._resolve_time(started_at)
        next_state = SessionState(
            kind=SessionStateKind.ACTIVE,
            session_id=normalized_id,
            started_at=event_time,
            last_activity_at=event_time,
        )
        return self._apply_transition(previous, next_state, reason_code="started")

    def record_activity(
        self,
        *,
        session_id: str,
        event_time: datetime | None = None,
    ) -> SessionTransitionResult:
        """Record activity heartbeat for active session."""
        active_state = self._require_active_session(session_id=session_id)
        observed_at = self._resolve_time(event_time)
        self._ensure_monotonic(observed_at, baseline=active_state.last_activity_at)
        next_state = replace(active_state, last_activity_at=observed_at)
        return self._apply_transition(
            active_state,
            next_state,
            reason_code="activity_recorded",
        )

    def stop_session(
        self,
        *,
        session_id: str,
        event_time: datetime | None = None,
    ) -> SessionTransitionResult:
        """Stop active session and mark completion."""
        active_state = self._require_active_session(session_id=session_id)
        observed_at = self._resolve_time(event_time)
        self._ensure_monotonic(observed_at, baseline=active_state.last_activity_at)
        next_state = SessionState(
            kind=SessionStateKind.COMPLETED,
            session_id=active_state.session_id,
            started_at=active_state.started_at,
            last_activity_at=active_state.last_activity_at,
            ended_at=observed_at,
            reason_code="stopped",
        )
        return self._apply_transition(active_state, next_state, reason_code="stopped")

    def abort_session(
        self,
        *,
        session_id: str,
        event_time: datetime | None = None,
        reason_code: str = "aborted",
    ) -> SessionTransitionResult:
        """Abort active session and mark terminal aborted state."""
        active_state = self._require_active_session(session_id=session_id)
        observed_at = self._resolve_time(event_time)
        self._ensure_monotonic(observed_at, baseline=active_state.last_activity_at)
        next_state = SessionState(
            kind=SessionStateKind.ABORTED,
            session_id=active_state.session_id,
            started_at=active_state.started_at,
            last_activity_at=active_state.last_activity_at,
            ended_at=observed_at,
            reason_code=str(reason_code),
        )
        return self._apply_transition(
            active_state,
            next_state,
            reason_code=str(reason_code),
        )

    def evaluate_timeouts(
        self,
        *,
        now: datetime | None = None,
    ) -> TimeoutEvaluation:
        """Evaluate current session timeout posture."""
        state = self._state
        if state.kind is not SessionStateKind.ACTIVE:
            return TimeoutEvaluation(
                outcome=TimeoutOutcome.NOT_STARTED,
                idle_elapsed_seconds=0.0,
                runtime_elapsed_seconds=0.0,
            )

        current_time = self._resolve_time(now)
        self._ensure_monotonic(current_time, baseline=state.started_at)
        self._ensure_monotonic(current_time, baseline=state.last_activity_at)

        started_at = state.started_at or current_time
        last_activity_at = state.last_activity_at or started_at
        runtime_elapsed = max(0.0, (current_time - started_at).total_seconds())
        idle_elapsed = max(0.0, (current_time - last_activity_at).total_seconds())

        max_runtime = self._policy.max_runtime_seconds
        if max_runtime is not None and runtime_elapsed >= max_runtime:
            return TimeoutEvaluation(
                outcome=TimeoutOutcome.HARD_TIMEOUT,
                idle_elapsed_seconds=idle_elapsed,
                runtime_elapsed_seconds=runtime_elapsed,
            )

        idle_timeout = self._policy.idle_timeout_seconds
        if idle_timeout is not None and idle_elapsed >= idle_timeout:
            return TimeoutEvaluation(
                outcome=TimeoutOutcome.SOFT_TIMEOUT,
                idle_elapsed_seconds=idle_elapsed,
                runtime_elapsed_seconds=runtime_elapsed,
            )

        return TimeoutEvaluation(
            outcome=TimeoutOutcome.STILL_ACTIVE,
            idle_elapsed_seconds=idle_elapsed,
            runtime_elapsed_seconds=runtime_elapsed,
        )

    def get_summary(self) -> SessionSummary:
        """Expose stable summary snapshot for runtime diagnostics."""
        return SessionSummary(
            state_kind=self._state.kind,
            session_id=self._state.session_id,
            started_at=self._state.started_at,
            last_activity_at=self._state.last_activity_at,
            ended_at=self._state.ended_at,
        )

    def _apply_transition(
        self,
        previous: SessionState,
        next_state: SessionState,
        *,
        reason_code: str,
    ) -> SessionTransitionResult:
        self._state = next_state
        warnings: list[str] = []
        pending = SessionTransitionResult(
            previous_state=previous,
            next_state=next_state,
            reason_code=reason_code,
            warnings=(),
        )
        for callback in self._transition_callbacks:
            try:
                callback(pending)
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"transition callback failed: {exc}")
        if not warnings:
            return pending
        return replace(pending, warnings=tuple(warnings))

    def _require_active_session(self, *, session_id: str) -> SessionState:
        state = self._state
        if state.kind is not SessionStateKind.ACTIVE or state.session_id is None:
            raise SessionNotStartedError("No active session is available.")

        normalized_id = _normalize_session_id(session_id)
        if state.session_id != normalized_id:
            raise SessionTransitionError(
                f"Session id mismatch: expected {state.session_id!r}, received {normalized_id!r}."
            )
        return state

    def _resolve_time(self, value: datetime | None) -> datetime:
        return value if value is not None else self._clock.now()

    @staticmethod
    def _ensure_monotonic(current: datetime, *, baseline: datetime | None) -> None:
        if baseline is not None and current < baseline:
            raise SessionTimeSourceError(
                "Clock regression detected during session timeout evaluation."
            )


def _normalize_session_id(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SessionTransitionError("session_id must be a non-empty string")
    return value.strip()
