"""PC configuration for the twin-screw extruder workstation."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ipat_watchdog.core.config import PCConfig, PathSettings


def build_config(override_paths: Optional[dict[str, Path]] = None) -> PCConfig:
    """Return the twin-screw extruder PC configuration."""

    paths = PathSettings()
    if override_paths:
        for key, value in override_paths.items():
            if hasattr(paths, key):
                setattr(paths, key, Path(value))

    return PCConfig(
        identifier="twinscrew_blb",
        name="Twin-Screw Extruder PC",
        location="Extrusion Lab",
        paths=paths,
        active_device_plugins=("etr_twinscrew",),
    )
