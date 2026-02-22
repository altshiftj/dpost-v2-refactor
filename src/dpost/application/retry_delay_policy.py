"""Shared retry-delay parsing and normalization helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryDelayPolicy:
    """Normalize retry delays with shared defaults and clamping rules."""

    default_delay_seconds: float = 2.0
    minimum_delay_seconds: float = 0.1

    def coerce(self, raw_delay: object) -> float:
        """Parse delay-like values, falling back to the policy default on error."""
        try:
            return float(raw_delay)
        except Exception:
            return self.default_delay_seconds

    def normalize(self, raw_delay: object) -> float:
        """Parse and clamp a delay to the configured minimum."""
        return max(self.coerce(raw_delay), self.minimum_delay_seconds)
