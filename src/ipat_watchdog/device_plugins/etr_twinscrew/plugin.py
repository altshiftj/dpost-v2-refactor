"""Device plugin wiring for the ETR twin-screw extruder."""

from __future__ import annotations

from ipat_watchdog.core.config import DeviceConfig
from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS
from ipat_watchdog.device_plugins.device_plugin import DevicePlugin
from ipat_watchdog.device_plugins.etr_twinscrew.file_processor import (
    ETRTwinScrewFileProcessor,
)
from ipat_watchdog.device_plugins.etr_twinscrew.settings import build_config


class ETRTwinScrewPlugin(DevicePlugin):
    """Registers the ETR twin-screw extruder with the Watchdog application."""

    def __init__(self) -> None:
        self._config = build_config()
        self._processor = ETRTwinScrewFileProcessor(self._config)

    def get_config(self) -> DeviceConfig:
        return self._config

    def get_file_processor(self) -> FileProcessorABS:
        return self._processor
