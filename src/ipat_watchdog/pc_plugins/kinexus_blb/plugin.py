"""PC plugin that configures the BLB Kinexus acquisition workstation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ipat_watchdog.core.config import PCConfig
from ipat_watchdog.pc_plugins.kinexus_blb.settings import build_config
from ipat_watchdog.pc_plugins.pc_plugin import PCPlugin
from ipat_watchdog.plugin_system import hookimpl

if TYPE_CHECKING:
    from ipat_watchdog.plugin_system import PCPluginRegistry


class PCKinexusPlugin(PCPlugin):
    """Kinexus BLB PC plugin with optimised configuration."""

    def __init__(self) -> None:
        self._config = build_config()

    def get_config(self) -> PCConfig:
        return self._config


@hookimpl
def register_pc_plugins(registry: "PCPluginRegistry") -> None:
    registry.register("kinexus_blb", PCKinexusPlugin)
