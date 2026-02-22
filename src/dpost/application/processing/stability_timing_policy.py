"""Pure timing policy resolution for the file stability tracker."""

from __future__ import annotations

from dataclasses import dataclass

from dpost.application.config import DeviceConfig, StabilityOverride


@dataclass(frozen=True)
class StabilityTimingPolicy:
    """Resolved timing thresholds used by stability tracking loops."""

    poll_seconds: float
    max_wait_seconds: int
    stable_cycles: int
    reappear_window_seconds: float


def resolve_stability_timing_policy(
    device: DeviceConfig | None,
    override: StabilityOverride | None,
) -> StabilityTimingPolicy:
    """Resolve effective stability timing values from device + optional override."""
    poll_seconds = _resolve_poll_seconds(device, override)
    max_wait_seconds = _resolve_max_wait_seconds(device, override)
    stable_cycles = _resolve_stable_cycles(device, override)
    reappear_window_seconds = _resolve_reappear_window_seconds(device)
    return StabilityTimingPolicy(
        poll_seconds=poll_seconds,
        max_wait_seconds=max_wait_seconds,
        stable_cycles=stable_cycles,
        reappear_window_seconds=reappear_window_seconds,
    )


def _resolve_poll_seconds(
    device: DeviceConfig | None,
    override: StabilityOverride | None,
) -> float:
    if override is not None and override.poll_seconds is not None:
        return max(float(override.poll_seconds), 0.0)
    if device is None:
        return 1.0
    return max(float(device.watcher.poll_seconds), 0.0)


def _resolve_max_wait_seconds(
    device: DeviceConfig | None,
    override: StabilityOverride | None,
) -> int:
    if override is not None and override.max_wait_seconds is not None:
        return int(override.max_wait_seconds)
    if device is None:
        return 300
    return int(device.watcher.max_wait_seconds)


def _resolve_stable_cycles(
    device: DeviceConfig | None,
    override: StabilityOverride | None,
) -> int:
    if override is not None and override.stable_cycles is not None:
        return int(override.stable_cycles)
    if device is None:
        return 3
    return int(device.watcher.stable_cycles)


def _resolve_reappear_window_seconds(device: DeviceConfig | None) -> float:
    """Return optional disappear/reappear grace period in seconds (0 disables)."""
    if device is None:
        return 0.0
    try:
        value = getattr(device.watcher, "reappear_window_seconds", 0.0)
        return float(value) if value else 0.0
    except Exception:
        return 0.0
