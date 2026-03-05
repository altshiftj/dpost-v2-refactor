"""Device plugin wiring for the Kinexus Pro+ rheometer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ipat_watchdog.core.config import DeviceConfig
from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS
from ipat_watchdog.device_plugins.device_plugin import DevicePlugin
from ipat_watchdog.device_plugins.rhe_kinexus.file_processor import (
    FileProcessorRHEKinexus,
)
from ipat_watchdog.device_plugins.rhe_kinexus.settings import build_config
from ipat_watchdog.plugin_system import hookimpl

if TYPE_CHECKING:
    from ipat_watchdog.plugin_system import DevicePluginRegistry


class RheKinexusPlugin(DevicePlugin):
    """Registers the Kinexus Pro+ device with the Watchdog app."""

    def __init__(self) -> None:
        self._config = build_config()
        self._processor = FileProcessorRHEKinexus(self._config)

    def get_config(self) -> DeviceConfig:
        return self._config

    def get_file_processor(self) -> FileProcessorABS:
        return self._processor


@hookimpl
def register_device_plugins(registry: "DevicePluginRegistry") -> None:
    registry.register("rhe_kinexus", RheKinexusPlugin)
