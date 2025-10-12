"""PC plugin entry point for the Mischraum extruder environment."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ipat_watchdog.core.config import PCConfig
from ipat_watchdog.pc_plugins.pc_plugin import PCPlugin
from ipat_watchdog.pc_plugins.haake_blb.settings import build_config


class PCHaakePlugin(PCPlugin):
    """Exposes the Mischraum extruder workstation configuration."""

    def __init__(self, override_paths: Optional[dict[str, Path]] = None) -> None:
        self._config = build_config(override_paths=override_paths)

    def get_config(self) -> PCConfig:
        return self._config
