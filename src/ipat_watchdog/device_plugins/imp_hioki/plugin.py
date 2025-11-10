"""Device plugin wiring for Hioki analyzer exports."""
from __future__ import annotations

from ipat_watchdog.device_plugins.device_plugin import DevicePlugin
from ipat_watchdog.device_plugins.imp_hioki.settings import build_config
from ipat_watchdog.device_plugins.imp_hioki.file_processor import FileProcessorHioki
from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS
from ipat_watchdog.core.config import DeviceConfig
from ipat_watchdog.plugin_system import DevicePluginRegistry, hookimpl


class HiokiAnalyzerPlugin(DevicePlugin):
    """Registers the Hioki analyzer device with the Watchdog app."""

    def __init__(self) -> None:
        self._config = build_config()
        self._processor = FileProcessorHioki(self._config)

    def get_config(self) -> DeviceConfig:
        return self._config

    def get_file_processor(self) -> FileProcessorABS:
        return self._processor

@hookimpl
def register_device_plugins(registry: "DevicePluginRegistry") -> None:
    registry.register("imp_hioki", HiokiAnalyzerPlugin)