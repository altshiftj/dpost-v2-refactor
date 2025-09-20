"""Device plugin for the Zwick UTM tensile testing instrument."""

from __future__ import annotations

from ipat_watchdog.device_plugins.device_plugin import DevicePlugin
from ipat_watchdog.device_plugins.utm_zwick.settings import build_config
from ipat_watchdog.device_plugins.utm_zwick.file_processor import FileProcessorZwickUTM
from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS
from ipat_watchdog.core.config import DeviceConfig


class UTMZwickPlugin(DevicePlugin):
    """Registers the Zwick UTM device with the Watchdog app."""

    def __init__(self) -> None:
        self._config = build_config()
        self._processor = FileProcessorZwickUTM()

    def get_config(self) -> DeviceConfig:
        return self._config

    def get_file_processor(self) -> FileProcessorABS:
        return self._processor
