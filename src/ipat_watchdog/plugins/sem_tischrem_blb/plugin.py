# src/ipat_watchdog/plugins/sem_tischrem_blb/plugin.py
from __future__ import annotations

from ipat_watchdog.plugins.device_plugin import DevicePlugin
from ipat_watchdog.plugins.sem_tischrem_blb.settings import TischREMSettings
from ipat_watchdog.plugins.sem_tischrem_blb.file_processor import FileProcessorTischREM
from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS
from ipat_watchdog.core.config.settings_base import BaseSettings

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
