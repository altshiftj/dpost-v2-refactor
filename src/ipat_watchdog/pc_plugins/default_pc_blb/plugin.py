from __future__ import annotations

from ipat_watchdog.pc_plugins.pc_plugin import PCPlugin
from ipat_watchdog.pc_plugins.default_pc_blb.settings import DefaultPCSettings
from ipat_watchdog.core.config.global_settings import PCSettings

class DefaultPCPlugin(PCPlugin):
    """Default PC plugin that provides standard PCSettings configuration."""

    def __init__(self) -> None:
        self._settings = DefaultPCSettings()

    # ---- PCPlugin contract ---------------------------------------------

    def get_settings(self) -> PCSettings:
        return self._settings
