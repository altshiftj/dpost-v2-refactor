from __future__ import annotations

from ipat_watchdog.pc_plugins.pc_plugin import PCPlugin
from ipat_watchdog.pc_plugins.horiba_blb.settings import PCHoribaSettings
from ipat_watchdog.core.config.pc_settings import PCSettings

class PCHoribaPlugin(PCPlugin):
    """Horiba BLB PC plugin with optimized settings for Horiba environments."""

    def __init__(self) -> None:
        self._settings = PCHoribaSettings()

    # ---- PCPlugin contract ---------------------------------------------

    def get_settings(self) -> PCSettings:
        return self._settings
