"""Device plugin registration for the Thermo Phenom XL2 SEM."""

from __future__ import annotations

from ipat_watchdog.device_plugins.device_plugin import DevicePlugin
from ipat_watchdog.device_plugins.sem_phenomxl2.settings import build_config
from ipat_watchdog.device_plugins.sem_phenomxl2.file_processor import FileProcessorSEMPhenomXL2
from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS
from ipat_watchdog.core.config import DeviceConfig


class SEMPhenomXL2Plugin(DevicePlugin):
    """Registers the Phenom XL TischREM device with the Watchdog app."""

    def __init__(self) -> None:
        self._config = build_config()
        self._processor = FileProcessorSEMPhenomXL2()

    def get_config(self) -> DeviceConfig:
        return self._config

    def get_file_processor(self) -> FileProcessorABS:
        return self._processor
