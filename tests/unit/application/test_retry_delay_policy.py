"""Unit tests for shared retry-delay parsing and normalization policy."""

from __future__ import annotations

from dpost.application.retry_delay_policy import RetryDelayPolicy


def test_retry_delay_policy_coerce_uses_default_on_invalid_input() -> None:
    """Invalid retry delay values should fall back to the configured default."""
    policy = RetryDelayPolicy(default_delay_seconds=2.5)

    assert policy.coerce("bad") == 2.5


def test_retry_delay_policy_normalize_clamps_to_minimum() -> None:
    """Normalization should enforce the configured minimum retry delay."""
    policy = RetryDelayPolicy(default_delay_seconds=2.0, minimum_delay_seconds=0.25)

    assert policy.normalize(0.0) == 0.25
    assert policy.normalize(1.5) == 1.5
