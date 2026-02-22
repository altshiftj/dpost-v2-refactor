"""Unit tests for pure stability timing policy resolution helpers."""

from __future__ import annotations

from dpost.application.config import DeviceConfig, StabilityOverride, WatcherSettings
from dpost.application.processing.stability_timing_policy import (
    resolve_stability_timing_policy,
)


def test_resolve_stability_timing_policy_defaults_without_device() -> None:
    """Use built-in timing defaults when no device config is available."""
    policy = resolve_stability_timing_policy(device=None, override=None)

    assert policy.poll_seconds == 1.0
    assert policy.max_wait_seconds == 300
    assert policy.stable_cycles == 3
    assert policy.reappear_window_seconds == 0.0


def test_resolve_stability_timing_policy_uses_override_values_when_present() -> None:
    """Override values should take precedence over watcher timing fields."""
    device = DeviceConfig(
        identifier="dev",
        watcher=WatcherSettings(
            poll_seconds=5.0,
            max_wait_seconds=20.0,
            stable_cycles=6,
            reappear_window_seconds=1.5,
        ),
    )
    override = StabilityOverride(
        suffixes=(".dat",),
        poll_seconds=-0.2,
        max_wait_seconds=2,
        stable_cycles=1,
    )

    policy = resolve_stability_timing_policy(device=device, override=override)

    assert policy.poll_seconds == 0.0
    assert policy.max_wait_seconds == 2
    assert policy.stable_cycles == 1
    assert policy.reappear_window_seconds == 1.5


def test_resolve_stability_timing_policy_falls_back_to_device_when_override_partial() -> None:
    """Unset override fields should fall back to the device watcher configuration."""
    device = DeviceConfig(
        identifier="dev",
        watcher=WatcherSettings(
            poll_seconds=0.25,
            max_wait_seconds=9.0,
            stable_cycles=4,
            reappear_window_seconds=0.75,
        ),
    )
    override = StabilityOverride(suffixes=(".csv",), poll_seconds=None, stable_cycles=None)

    policy = resolve_stability_timing_policy(device=device, override=override)

    assert policy.poll_seconds == 0.25
    assert policy.max_wait_seconds == 9
    assert policy.stable_cycles == 4
    assert policy.reappear_window_seconds == 0.75


def test_resolve_stability_timing_policy_invalid_reappear_window_defaults_zero() -> None:
    """Malformed watcher reappear-window values should safely normalize to zero."""
    device = DeviceConfig(identifier="dev", watcher=WatcherSettings())
    device.watcher.reappear_window_seconds = "bad"

    policy = resolve_stability_timing_policy(device=device, override=None)

    assert policy.reappear_window_seconds == 0.0
