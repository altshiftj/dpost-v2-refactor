"""PC configuration for the dpost HIOKI BLB workstation plugin."""

from __future__ import annotations

from dpost.application.config import PCConfig


def build_config() -> PCConfig:
    """Return the HIOKI BLB PC configuration."""
    return PCConfig(
        identifier="hioki_blb",
        active_device_plugins=("erm_hioki",),
    )
