"""Retry planning helpers for deferred processing results."""

from __future__ import annotations

from dataclasses import dataclass

from dpost.application.processing import ProcessingResult, ProcessingStatus
from dpost.application.retry_delay_policy import RetryDelayPolicy


@dataclass(frozen=True)
class RetryPlan:
    """Describes a delayed requeue request for a source path."""

    path: str
    delay_seconds: float


def build_retry_plan(
    src_path: str,
    result: ProcessingResult | None,
    *,
    default_delay_seconds: float,
    minimum_delay_seconds: float = 0.1,
) -> RetryPlan | None:
    """Return a normalized retry plan when a processing result is deferred."""
    if result is None:
        return None
    if result.status is not ProcessingStatus.DEFERRED:
        return None

    policy = RetryDelayPolicy(
        default_delay_seconds=default_delay_seconds,
        minimum_delay_seconds=minimum_delay_seconds,
    )
    raw_delay = (
        result.retry_delay if result.retry_delay is not None else default_delay_seconds
    )
    safe_delay = policy.normalize(raw_delay)
    return RetryPlan(path=src_path, delay_seconds=safe_delay)
