from __future__ import annotations

from ipat_watchdog.pc_plugins.pc_plugin import PCPlugin
from ipat_watchdog.pc_plugins.lab_workstation_blb.settings import LabWorkstationSettings
from ipat_watchdog.core.config.global_settings import PCSettings

class LabWorkstationPlugin(PCPlugin):
    """Lab workstation PC plugin with optimized settings for active lab environments."""

    def __init__(self) -> None:
        self._settings = LabWorkstationSettings()

    # ---- PCPlugin contract ---------------------------------------------

    def get_settings(self) -> PCSettings:
        return self._settings
