"""Device plugin wiring for the ETR twin-screw extruder."""

from __future__ import annotations

from ipat_watchdog.core.config import DeviceConfig
from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS
from ipat_watchdog.device_plugins.device_plugin import DevicePlugin
from ipat_watchdog.device_plugins.extr_haake.file_processor import (FileProcessorEXTRHaake,)
from ipat_watchdog.device_plugins.extr_haake.settings import build_config
from ipat_watchdog.plugin_system import DevicePluginRegistry, hookimpl


class EXTRHaakePlugin(DevicePlugin):
    """Registers the ETR twin-screw extruder with the Watchdog application."""

    def __init__(self) -> None:
        self._config = build_config()
        self._processor = FileProcessorEXTRHaake(self._config)

    def get_config(self) -> DeviceConfig:
        return self._config

    def get_file_processor(self) -> FileProcessorABS:
        return self._processor

@hookimpl
def register_device_plugins(registry: "DevicePluginRegistry") -> None:
    registry.register("extr_haake", EXTRHaakePlugin)
