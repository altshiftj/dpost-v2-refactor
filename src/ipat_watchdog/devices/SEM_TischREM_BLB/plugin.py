# devices/SEM_TischREM_BLB/plugin.py
from __future__ import annotations

from ipat_watchdog.devices.SEM_TischREM_BLB.settings_tischrem import TischREMSettings
from ipat_watchdog.devices.SEM_TischREM_BLB.file_processor_tischrem import FileProcessorTischREM
from ipat_watchdog.plugins.device_plugin import DevicePlugin
from ipat_watchdog.processing.file_processor_abstract import FileProcessorABS
from ipat_watchdog.config.settings_base import BaseSettings

class TischREMPlugin(DevicePlugin):
    """Registers the Phenom XL TischREM device with the Watchdog app."""

    def __init__(self) -> None:
        self._settings = TischREMSettings()
        self._processor = FileProcessorTischREM()

    # ---- DevicePlugin contract ---------------------------------------------

    def get_settings(self) -> BaseSettings:
        return self._settings

    def get_file_processor(self) -> FileProcessorABS:
        return self._processor
