"""Device plugin wiring for the Eirich mixer EL1."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ipat_watchdog.core.config import DeviceConfig
from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS
from ipat_watchdog.device_plugins.device_plugin import DevicePlugin
from ipat_watchdog.device_plugins.rmx_eirich_el1.file_processor import (
    FileProcessorEirich,
)
from ipat_watchdog.device_plugins.rmx_eirich_el1.settings import build_config
from ipat_watchdog.plugin_system import hookimpl

if TYPE_CHECKING:
    from ipat_watchdog.plugin_system import DevicePluginRegistry


class EirichMixerEL1Plugin(DevicePlugin):
    """Registers the Eirich EL1 mixer with the Watchdog app."""

    def __init__(self) -> None:
        self._config = build_config()
        self._processor = FileProcessorEirich(self._config)

    def get_config(self) -> DeviceConfig:
        return self._config

    def get_file_processor(self) -> FileProcessorABS:
        return self._processor


@hookimpl
def register_device_plugins(registry: "DevicePluginRegistry") -> None:
    # IMPORTANT: register the class (factory), not an instance
    registry.register("rmx_eirich_el1", EirichMixerEL1Plugin)
