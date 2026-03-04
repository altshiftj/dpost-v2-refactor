from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping


class ModifiedEventGateError(ValueError):
    """Base modified-event gate error."""


class ModifiedEventGateConfigError(ModifiedEventGateError):
    """Raised when debounce configuration is invalid."""


class ModifiedEventGateTimeError(ModifiedEventGateError):
    """Raised when event timestamps regress for a key."""


class ModifiedEventDecision(StrEnum):
    """Decision classes produced by modified-event gate policy."""

    ALLOW = "allow"
    DEFER = "defer"
    DROP_DUPLICATE = "drop_duplicate"


@dataclass(frozen=True, slots=True)
class ModifiedEventGateConfig:
    """Debounce configuration for duplicate modified events."""

    window_seconds: float


@dataclass(frozen=True, slots=True)
class ModifiedEventGateResult:
    """Gate decision payload with reason metadata."""

    decision: ModifiedEventDecision
    reason_code: str
    next_eligible_at: float | None = None
    diagnostics: Mapping[str, object] = field(default_factory=dict)


class ModifiedEventGate:
    """In-memory deterministic debounce gate keyed by event identity."""

    def __init__(self, config: ModifiedEventGateConfig) -> None:
        """Initialize gate with validated debounce configuration."""
        if config.window_seconds < 0:
            raise ModifiedEventGateConfigError("window_seconds must be non-negative.")
        self._config = config
        self._last_seen: dict[str, float] = {}

    def evaluate(self, event_key: str, event_timestamp: float) -> ModifiedEventGateResult:
        """Evaluate one event key/timestamp pair against debounce window state."""
        if not event_key:
            raise ModifiedEventGateConfigError("event_key must be non-empty.")

        last_seen = self._last_seen.get(event_key)
        if last_seen is not None and event_timestamp < last_seen:
            raise ModifiedEventGateTimeError(
                f"Timestamp regression for '{event_key}': {event_timestamp} < {last_seen}"
            )

        if last_seen is not None and (event_timestamp - last_seen) < self._config.window_seconds:
            next_eligible = last_seen + self._config.window_seconds
            return ModifiedEventGateResult(
                decision=ModifiedEventDecision.DROP_DUPLICATE,
                reason_code="inside_debounce_window",
                next_eligible_at=next_eligible,
            )

        self._last_seen[event_key] = event_timestamp
        return ModifiedEventGateResult(
            decision=ModifiedEventDecision.ALLOW,
            reason_code="outside_debounce_window",
        )
