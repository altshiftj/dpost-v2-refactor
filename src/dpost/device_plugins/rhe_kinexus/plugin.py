"""RHE KINEXUS device plugin registration under canonical dpost namespace."""

from __future__ import annotations

from typing import TYPE_CHECKING

from dpost.application.config import DeviceConfig
from dpost.application.processing.file_processor_abstract import FileProcessorABS
from dpost.device_plugins.rhe_kinexus.file_processor import FileProcessorRHEKinexus
from dpost.device_plugins.rhe_kinexus.settings import build_config
from dpost.plugins.system import hookimpl

if TYPE_CHECKING:
    from dpost.plugins.system import DevicePluginRegistry


class RheKinexusPlugin:
    """Register RHE KINEXUS device with canonical dpost plugin loader."""

    __test__ = False

    def __init__(self) -> None:
        self._config = build_config()
        self._processor = FileProcessorRHEKinexus(self._config)

    def get_config(self) -> DeviceConfig:
        return self._config

    def get_file_processor(self) -> FileProcessorABS:
        return self._processor


@hookimpl
def register_device_plugins(registry: "DevicePluginRegistry") -> None:
    """Register canonical RHE KINEXUS device plugin."""
    registry.register("rhe_kinexus", RheKinexusPlugin)
