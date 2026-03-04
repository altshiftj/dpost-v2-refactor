from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass
from enum import StrEnum


class RetryPlannerError(ValueError):
    """Base retry planner error."""


class RetryPlannerConfigError(RetryPlannerError):
    """Raised when retry configuration values are invalid."""


class RetryPlannerAttemptError(RetryPlannerError):
    """Raised when attempt index values are invalid."""


class RetryTerminalType(StrEnum):
    """Retry planner terminal types."""

    RETRY = "retry"
    STOP_RETRYING = "stop_retrying"


@dataclass(frozen=True, slots=True)
class RetryPlannerConfig:
    """Retry delay/backoff configuration."""

    max_attempts: int
    base_delay_seconds: float
    max_delay_seconds: float
    backoff_factor: float = 2.0
    jitter_ratio: float = 0.0


@dataclass(frozen=True, slots=True)
class RetryPlan:
    """Deterministic retry planning result."""

    terminal_type: RetryTerminalType
    delay_seconds: float
    next_attempt: int
    reason_code: str


def _validate_config(config: RetryPlannerConfig) -> None:
    if config.max_attempts <= 0:
        raise RetryPlannerConfigError("max_attempts must be greater than zero.")
    if config.base_delay_seconds < 0 or config.max_delay_seconds < 0:
        raise RetryPlannerConfigError("Delay values must be non-negative.")
    if config.backoff_factor <= 0:
        raise RetryPlannerConfigError("backoff_factor must be greater than zero.")
    if config.jitter_ratio < 0:
        raise RetryPlannerConfigError("jitter_ratio must be non-negative.")


def _deterministic_rng(seed: str) -> random.Random:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def plan_retry(
    *,
    config: RetryPlannerConfig,
    attempt_index: int,
    retryable: bool,
    seed: str = "",
) -> RetryPlan:
    """Plan deterministic retry delays with cap and jitter enforcement."""
    _validate_config(config)
    if attempt_index < 0:
        raise RetryPlannerAttemptError("attempt_index must be non-negative.")

    if not retryable:
        return RetryPlan(
            terminal_type=RetryTerminalType.STOP_RETRYING,
            delay_seconds=0.0,
            next_attempt=attempt_index,
            reason_code="non_retryable",
        )
    if attempt_index >= config.max_attempts:
        return RetryPlan(
            terminal_type=RetryTerminalType.STOP_RETRYING,
            delay_seconds=0.0,
            next_attempt=attempt_index,
            reason_code="attempt_cap_reached",
        )

    base_delay = config.base_delay_seconds * math.pow(
        config.backoff_factor, attempt_index
    )
    if math.isinf(base_delay) or math.isnan(base_delay):
        raise RetryPlannerConfigError("Invalid computed backoff delay.")

    jittered_delay = base_delay
    if config.jitter_ratio > 0:
        rng = _deterministic_rng(f"{seed}|{attempt_index}")
        span = base_delay * config.jitter_ratio
        jittered_delay = base_delay + rng.uniform(-span, span)

    clamped_delay = min(max(jittered_delay, 0.0), config.max_delay_seconds)
    return RetryPlan(
        terminal_type=RetryTerminalType.RETRY,
        delay_seconds=round(clamped_delay, 6),
        next_attempt=attempt_index + 1,
        reason_code="retry_scheduled",
    )
