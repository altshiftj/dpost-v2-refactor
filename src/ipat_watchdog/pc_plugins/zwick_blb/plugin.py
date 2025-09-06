from __future__ import annotations

from ipat_watchdog.pc_plugins.pc_plugin import PCPlugin
from ipat_watchdog.pc_plugins.zwick_blb.settings import PCZwickSettings
from ipat_watchdog.core.config.pc_settings import PCSettings

class PCZwickPlugin(PCPlugin):
    """Lab workstation PC plugin with optimized settings for active lab environments."""

    def __init__(self) -> None:
        self._settings = PCZwickSettings()

    # ---- PCPlugin contract ---------------------------------------------

    def get_settings(self) -> PCSettings:
        return self._settings
