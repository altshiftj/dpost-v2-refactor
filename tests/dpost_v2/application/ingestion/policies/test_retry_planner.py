from __future__ import annotations

import pytest

from dpost_v2.application.ingestion.policies.retry_planner import (
    RetryPlannerAttemptError,
    RetryPlannerConfig,
    RetryTerminalType,
    plan_retry,
)


def test_retry_planner_caps_at_max_attempts() -> None:
    config = RetryPlannerConfig(
        max_attempts=3,
        base_delay_seconds=2.0,
        max_delay_seconds=30.0,
        backoff_factor=2.0,
        jitter_ratio=0.0,
    )

    plan = plan_retry(config=config, attempt_index=3, retryable=True, seed="id-1")

    assert plan.terminal_type is RetryTerminalType.STOP_RETRYING
    assert plan.reason_code == "attempt_cap_reached"


def test_retry_planner_is_deterministic_with_seeded_jitter() -> None:
    config = RetryPlannerConfig(
        max_attempts=5,
        base_delay_seconds=4.0,
        max_delay_seconds=30.0,
        backoff_factor=2.0,
        jitter_ratio=0.25,
    )

    left = plan_retry(config=config, attempt_index=1, retryable=True, seed="same")
    right = plan_retry(config=config, attempt_index=1, retryable=True, seed="same")

    assert left.delay_seconds == right.delay_seconds
    assert left.terminal_type is RetryTerminalType.RETRY


def test_retry_planner_rejects_negative_attempt_index() -> None:
    config = RetryPlannerConfig(
        max_attempts=2,
        base_delay_seconds=1.0,
        max_delay_seconds=5.0,
        backoff_factor=2.0,
        jitter_ratio=0.0,
    )

    with pytest.raises(RetryPlannerAttemptError):
        plan_retry(config=config, attempt_index=-1, retryable=True)
