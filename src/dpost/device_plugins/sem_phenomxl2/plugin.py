"""SEM PHENOM XL2 device plugin registration under canonical dpost namespace."""

from __future__ import annotations

from typing import TYPE_CHECKING

from dpost.application.config import DeviceConfig
from dpost.application.processing.file_processor_abstract import FileProcessorABS
from dpost.device_plugins.sem_phenomxl2.file_processor import (
    FileProcessorSEMPhenomXL2,
)
from dpost.device_plugins.sem_phenomxl2.settings import build_config
from dpost.plugins.system import hookimpl

if TYPE_CHECKING:
    from dpost.plugins.system import DevicePluginRegistry


class SEMPhenomXL2Plugin:
    """Register SEM PHENOM XL2 device with canonical dpost plugin loader."""

    __test__ = False

    def __init__(self) -> None:
        self._config = build_config()
        self._processor = FileProcessorSEMPhenomXL2(self._config)

    def get_config(self) -> DeviceConfig:
        return self._config

    def get_file_processor(self) -> FileProcessorABS:
        return self._processor


@hookimpl
def register_device_plugins(registry: "DevicePluginRegistry") -> None:
    """Register canonical SEM PHENOM XL2 device plugin."""
    registry.register("sem_phenomxl2", SEMPhenomXL2Plugin)
