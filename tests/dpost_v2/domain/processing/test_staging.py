"""Unit tests for V2 domain staging state transitions."""

from __future__ import annotations

import pytest

from dpost_v2.domain.processing.staging import (
    StagingAttemptOrderError,
    StagingEvent,
    StagingReasonRequiredError,
    StagingState,
    StagingStateUnknownError,
    StagingTransitionError,
    is_terminal_state,
    transition_state,
)


def test_transition_state_allows_valid_success_path() -> None:
    """Allow the canonical success path through staging finite-state transitions."""
    step_1 = transition_state(StagingState.OBSERVED, StagingEvent.STABILIZED)
    step_2 = transition_state(step_1.next_state, StagingEvent.ROUTED)
    step_3 = transition_state(step_2.next_state, StagingEvent.PERSISTED)

    assert step_1.next_state is StagingState.STABILIZED
    assert step_2.next_state is StagingState.ROUTED
    assert step_3.next_state is StagingState.PERSISTED
    assert step_3.trace.to_state is StagingState.PERSISTED


def test_transition_state_rejects_outgoing_transition_from_terminal_state() -> None:
    """Terminal staging states should have no outbound transitions."""
    with pytest.raises(StagingTransitionError):
        transition_state(StagingState.PERSISTED, StagingEvent.ROUTED)


def test_transition_state_rejects_illegal_state_event_pair() -> None:
    """Reject unsupported state/event combinations with typed errors."""
    with pytest.raises(StagingTransitionError):
        transition_state(StagingState.OBSERVED, StagingEvent.PERSISTED)


def test_transition_state_requires_reason_for_failure_paths() -> None:
    """Require reason code for failure and rejection transitions."""
    with pytest.raises(StagingReasonRequiredError):
        transition_state(StagingState.ROUTED, StagingEvent.FAILED)


def test_transition_state_rejects_attempt_index_regression() -> None:
    """Attempt index should be monotonic when provided."""
    with pytest.raises(StagingAttemptOrderError):
        transition_state(
            StagingState.ROUTED,
            StagingEvent.FAILED,
            reason_code="io_error",
            attempt_index=1,
            previous_attempt_index=2,
        )


def test_transition_state_rejects_unknown_source_state() -> None:
    """Reject unknown state tokens before transition lookup."""
    with pytest.raises(StagingStateUnknownError):
        transition_state("not_a_state", StagingEvent.STABILIZED)


def test_is_terminal_state_identifies_terminal_and_non_terminal_states() -> None:
    """Expose deterministic helper for terminal-state checks."""
    assert is_terminal_state(StagingState.PERSISTED) is True
    assert is_terminal_state(StagingState.FAILED) is True
    assert is_terminal_state(StagingState.REJECTED) is True
    assert is_terminal_state(StagingState.ROUTED) is False
