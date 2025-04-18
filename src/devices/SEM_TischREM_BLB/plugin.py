# devices/SEM_TischREM_BLB/plugin.py
from __future__ import annotations

from devices.SEM_TischREM_BLB.settings_tischrem import TischREMSettings
from devices.SEM_TischREM_BLB.file_processor_tischrem import FileProcessorTischREM
from plugins.device_plugin import DevicePlugin
from processing.file_processor_abstract import FileProcessorABS
from config.settings_base import BaseSettings

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
