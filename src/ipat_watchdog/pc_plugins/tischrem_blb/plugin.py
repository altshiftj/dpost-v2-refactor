from __future__ import annotations

from ipat_watchdog.pc_plugins.pc_plugin import PCPlugin
from ipat_watchdog.pc_plugins.tischrem_blb.settings import PCTischREMSettings
from ipat_watchdog.core.config.pc_settings import PCSettings

class PCTischREMPlugin(PCPlugin):
    """Lab workstation PC plugin with optimized settings for active lab environments."""

    def __init__(self) -> None:
        self._settings = PCTischREMSettings()

    # ---- PCPlugin contract ---------------------------------------------

    def get_settings(self) -> PCSettings:
        return self._settings
