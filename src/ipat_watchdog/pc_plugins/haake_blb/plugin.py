"""PC plugin entry point for the Mischraum extruder environment."""

from __future__ import annotations


from ipat_watchdog.core.config import PCConfig
from ipat_watchdog.pc_plugins.pc_plugin import PCPlugin
from ipat_watchdog.pc_plugins.haake_blb.settings import build_config
from ipat_watchdog.plugin_system import PCPluginRegistry, hookimpl


class PCHaakePlugin(PCPlugin):
    """Exposes the Mischraum extruder workstation configuration."""

    def __init__(self) -> None:
        self._config = build_config()

    def get_config(self) -> PCConfig:
        return self._config

@hookimpl
def register_pc_plugins(registry: "PCPluginRegistry") -> None:
    registry.register("haake_blb", PCHaakePlugin)