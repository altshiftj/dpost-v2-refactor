"""Factory helpers for dpost reference test PC configuration."""

from __future__ import annotations

from pathlib import Path

from dpost.application.config import PathSettings, PCConfig


def build_config(override_paths: dict[str, Path] | None = None) -> PCConfig:
    """Return the lightweight PC configuration used by dpost reference tests."""
    paths = PathSettings()
    if override_paths:
        for key, value in override_paths.items():
            if hasattr(paths, key):
                setattr(paths, key, Path(value))
    return PCConfig(
        identifier="test_pc",
        name="TEST_PC",
        location="Test Lab",
        paths=paths,
        active_device_plugins=("test_device",),
    )
