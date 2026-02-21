"""EXTR HAAKE device plugin registration under canonical dpost namespace."""

from __future__ import annotations

from typing import TYPE_CHECKING

from dpost.application.config import DeviceConfig
from dpost.application.processing.file_processor_abstract import FileProcessorABS
from dpost.device_plugins.extr_haake.file_processor import FileProcessorEXTRHaake
from dpost.device_plugins.extr_haake.settings import build_config
from dpost.plugins.system import hookimpl

if TYPE_CHECKING:
    from dpost.plugins.system import DevicePluginRegistry


class EXTRHaakePlugin:
    """Register EXTR HAAKE device with canonical dpost plugin loader."""

    __test__ = False

    def __init__(self) -> None:
        self._config = build_config()
        self._processor = FileProcessorEXTRHaake(self._config)

    def get_config(self) -> DeviceConfig:
        return self._config

    def get_file_processor(self) -> FileProcessorABS:
        return self._processor


@hookimpl
def register_device_plugins(registry: "DevicePluginRegistry") -> None:
    """Register canonical EXTR HAAKE device plugin."""
    registry.register("extr_haake", EXTRHaakePlugin)
