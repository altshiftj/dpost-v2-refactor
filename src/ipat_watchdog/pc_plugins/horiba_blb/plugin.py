"""PC plugin that configures the BLB Horiba acquisition workstation."""

from __future__ import annotations

from ipat_watchdog.pc_plugins.pc_plugin import PCPlugin
from ipat_watchdog.pc_plugins.horiba_blb.settings import build_config
from ipat_watchdog.core.config import PCConfig


class PCHoribaPlugin(PCPlugin):
    """Horiba BLB PC plugin with optimised configuration."""

    def __init__(self) -> None:
        self._config = build_config()

    def get_config(self) -> PCConfig:
        return self._config
