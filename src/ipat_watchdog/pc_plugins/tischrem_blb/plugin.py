"""PC plugin for the Tisch REM workstation setup."""

from __future__ import annotations

from ipat_watchdog.pc_plugins.pc_plugin import PCPlugin
from ipat_watchdog.pc_plugins.tischrem_blb.settings import build_config
from ipat_watchdog.core.config import PCConfig


class PCTischREMPlugin(PCPlugin):
    """Lab workstation PC plugin with optimised settings."""

    def __init__(self) -> None:
        self._config = build_config()

    def get_config(self) -> PCConfig:
        return self._config
