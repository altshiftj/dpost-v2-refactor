"""Device plugin wiring for the Eirich mixer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ipat_watchdog.core.config import DeviceConfig
from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS
from ipat_watchdog.device_plugins.device_plugin import DevicePlugin
from ipat_watchdog.device_plugins.mix_eirich.file_processor import FileProcessorEirich
from ipat_watchdog.device_plugins.mix_eirich.settings import build_config
from ipat_watchdog.plugin_system import hookimpl

if TYPE_CHECKING:
    from ipat_watchdog.plugin_system import DevicePluginRegistry


class EirichMixerPlugin(DevicePlugin):
    """Registers a specific Eirich mixer variant with the Watchdog app."""

    def __init__(self, variant: str) -> None:
        self._config = build_config(variant)
        self._processor = FileProcessorEirich(self._config)

    def get_config(self) -> DeviceConfig:
        return self._config

    def get_file_processor(self) -> FileProcessorABS:
        return self._processor


class EirichMixerEL1Plugin(EirichMixerPlugin):
    def __init__(self) -> None:
        super().__init__("EL1")


class EirichMixerR01Plugin(EirichMixerPlugin):
    def __init__(self) -> None:
        super().__init__("R01")


@hookimpl
def register_device_plugins(registry: "DevicePluginRegistry") -> None:
    # IMPORTANT: register the class (factory), not an instance
    registry.register("rmx_eirich_el1", EirichMixerEL1Plugin)
    registry.register("rmx_eirich_r01", EirichMixerR01Plugin)
