"""Retry planning helpers for deferred processing results."""

from __future__ import annotations

from dataclasses import dataclass

from dpost.application.processing import ProcessingResult, ProcessingStatus


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

    raw_delay = result.retry_delay
    if raw_delay is None:
        resolved_delay = default_delay_seconds
    else:
        try:
            resolved_delay = float(raw_delay)
        except Exception:
            resolved_delay = default_delay_seconds

    safe_delay = max(resolved_delay, minimum_delay_seconds)
    return RetryPlan(path=src_path, delay_seconds=safe_delay)
