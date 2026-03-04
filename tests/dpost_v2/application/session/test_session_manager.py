from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest

from dpost_v2.application.session.session_manager import (
    SessionManager,
    SessionNotStartedError,
    SessionPolicy,
    SessionStateKind,
    SessionTimeSourceError,
    SessionTransitionError,
    TimeoutOutcome,
)


@dataclass
class FakeClock:
    current: datetime

    def now(self) -> datetime:
        return self.current


def _utc(iso_value: str) -> datetime:
    return datetime.fromisoformat(iso_value).astimezone(UTC)


def test_start_session_is_idempotent_for_identical_session_id() -> None:
    clock = FakeClock(_utc("2026-03-04T10:00:00+00:00"))
    manager = SessionManager(
        policy=SessionPolicy(idle_timeout_seconds=60.0, max_runtime_seconds=300.0),
        clock=clock,
    )

    started = manager.start_session(session_id="session-001")
    started_again = manager.start_session(session_id="session-001")

    assert started.previous_state.kind is SessionStateKind.INACTIVE
    assert started.next_state.kind is SessionStateKind.ACTIVE
    assert started.reason_code == "started"
    assert started_again.reason_code == "idempotent_start"
    assert started_again.next_state == started.next_state


def test_start_session_rejects_different_session_id_when_active() -> None:
    clock = FakeClock(_utc("2026-03-04T10:01:00+00:00"))
    manager = SessionManager(policy=SessionPolicy(), clock=clock)
    manager.start_session(session_id="session-001")

    with pytest.raises(SessionTransitionError, match="session-001"):
        manager.start_session(session_id="session-002")


def test_record_activity_requires_active_session() -> None:
    manager = SessionManager(
        policy=SessionPolicy(idle_timeout_seconds=45.0),
        clock=FakeClock(_utc("2026-03-04T10:02:00+00:00")),
    )

    with pytest.raises(SessionNotStartedError):
        manager.record_activity(session_id="missing-session")


def test_timeout_evaluation_classifies_soft_then_hard_timeout() -> None:
    clock = FakeClock(_utc("2026-03-04T10:03:00+00:00"))
    manager = SessionManager(
        policy=SessionPolicy(idle_timeout_seconds=30.0, max_runtime_seconds=120.0),
        clock=clock,
    )
    manager.start_session(session_id="session-003")

    clock.current = clock.current + timedelta(seconds=10)
    manager.record_activity(session_id="session-003")

    clock.current = clock.current + timedelta(seconds=20)
    still_active = manager.evaluate_timeouts()
    assert still_active.outcome is TimeoutOutcome.STILL_ACTIVE

    clock.current = clock.current + timedelta(seconds=11)
    soft_timeout = manager.evaluate_timeouts()
    assert soft_timeout.outcome is TimeoutOutcome.SOFT_TIMEOUT

    clock.current = _utc("2026-03-04T10:05:30+00:00")
    hard_timeout = manager.evaluate_timeouts()
    assert hard_timeout.outcome is TimeoutOutcome.HARD_TIMEOUT


def test_evaluate_timeouts_rejects_clock_regression() -> None:
    clock = FakeClock(_utc("2026-03-04T10:06:00+00:00"))
    manager = SessionManager(
        policy=SessionPolicy(idle_timeout_seconds=60.0, max_runtime_seconds=300.0),
        clock=clock,
    )
    manager.start_session(session_id="session-004")

    clock.current = clock.current + timedelta(seconds=25)
    manager.record_activity(session_id="session-004")

    clock.current = _utc("2026-03-04T10:06:10+00:00")
    with pytest.raises(SessionTimeSourceError, match="regression"):
        manager.evaluate_timeouts()


def test_transition_callback_failures_are_captured_as_warnings() -> None:
    clock = FakeClock(_utc("2026-03-04T10:07:00+00:00"))

    def failing_callback(_transition) -> None:
        raise RuntimeError("callback broke")

    manager = SessionManager(
        policy=SessionPolicy(),
        clock=clock,
        transition_callbacks=(failing_callback,),
    )

    result = manager.start_session(session_id="session-005")

    assert result.next_state.kind is SessionStateKind.ACTIVE
    assert result.warnings == ("transition callback failed: callback broke",)
    assert manager.state.kind is SessionStateKind.ACTIVE
