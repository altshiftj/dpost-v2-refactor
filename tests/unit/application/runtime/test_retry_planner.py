"""Unit tests for deferred retry planning helpers."""

from __future__ import annotations

from dpost.application.processing import ProcessingResult, ProcessingStatus
from dpost.application.runtime.retry_planner import RetryPlan, build_retry_plan


def test_build_retry_plan_returns_none_for_missing_result() -> None:
    assert build_retry_plan("path.txt", None, default_delay_seconds=2.0) is None


def test_build_retry_plan_returns_none_for_non_deferred_result() -> None:
    result = ProcessingResult(status=ProcessingStatus.PROCESSED, message="done")
    assert build_retry_plan("path.txt", result, default_delay_seconds=2.0) is None


def test_build_retry_plan_uses_default_when_delay_not_provided() -> None:
    result = ProcessingResult(status=ProcessingStatus.DEFERRED, message="wait")
    plan = build_retry_plan("path.txt", result, default_delay_seconds=2.5)

    assert plan == RetryPlan(path="path.txt", delay_seconds=2.5)


def test_build_retry_plan_clips_to_minimum_delay() -> None:
    result = ProcessingResult(
        status=ProcessingStatus.DEFERRED,
        message="wait",
        retry_delay=0.0,
    )
    plan = build_retry_plan("path.txt", result, default_delay_seconds=1.0)

    assert plan == RetryPlan(path="path.txt", delay_seconds=0.1)


def test_build_retry_plan_falls_back_to_default_for_invalid_delay() -> None:
    result = ProcessingResult(
        status=ProcessingStatus.DEFERRED,
        message="wait",
        retry_delay="bad",  # type: ignore[arg-type]
    )
    plan = build_retry_plan("path.txt", result, default_delay_seconds=3.0)

    assert plan == RetryPlan(path="path.txt", delay_seconds=3.0)
