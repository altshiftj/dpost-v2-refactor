from __future__ import annotations

from pathlib import Path
from typing import Optional

from ipat_watchdog.core.config import PCConfig, PathSettings


def build_config(override_paths: Optional[dict[str, Path]] = None) -> PCConfig:
    """Return the lightweight PC configuration used in automated tests."""
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
