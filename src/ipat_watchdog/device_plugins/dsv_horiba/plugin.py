from __future__ import annotations

from ipat_watchdog.device_plugins.device_plugin import DevicePlugin
from ipat_watchdog.device_plugins.dsv_horiba.settings import build_config
from ipat_watchdog.device_plugins.dsv_horiba.file_processor import FileProcessorDSVHoriba
from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS
from ipat_watchdog.core.config import DeviceConfig


class DSVHoribaPlugin(DevicePlugin):
    """Registers the Horiba Dissolver device with the Watchdog app."""

    def __init__(self) -> None:
        self._config = build_config()
        self._processor = FileProcessorDSVHoriba()

    def get_config(self) -> DeviceConfig:
        return self._config

    def get_file_processor(self) -> FileProcessorABS:
        return self._processor
