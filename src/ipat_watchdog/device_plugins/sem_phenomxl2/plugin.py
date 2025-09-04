# src/ipat_watchdog/plugins/sem_phenomxl2/plugin.py
from __future__ import annotations

from ipat_watchdog.device_plugins.device_plugin import DevicePlugin
from ipat_watchdog.device_plugins.sem_phenomxl2.settings import SEMPhenomXL2Settings
from ipat_watchdog.device_plugins.sem_phenomxl2.file_processor import FileProcessorSEMPhenomXL2
from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS
from ipat_watchdog.core.config.settings_base import BaseSettings

class SEMPhenomXL2Plugin(DevicePlugin):
    """Registers the Phenom XL TischREM device with the Watchdog app."""

    def __init__(self) -> None:
        self._settings = SEMPhenomXL2Settings()
        self._processor = FileProcessorSEMPhenomXL2()

    # ---- DevicePlugin contract ---------------------------------------------

    def get_settings(self) -> BaseSettings:
        return self._settings

    def get_file_processor(self) -> FileProcessorABS:
        return self._processor
