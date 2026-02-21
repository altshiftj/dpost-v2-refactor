"""Reference dpost device plugin used for runtime validation paths."""

from __future__ import annotations

from typing import TYPE_CHECKING

from dpost.application.config import DeviceConfig
from dpost.device_plugins.test_device.file_processor import TestFileProcessor
from dpost.device_plugins.test_device.settings import build_config
from dpost.plugins.system import hookimpl

if TYPE_CHECKING:
    from dpost.plugins.system import DevicePluginRegistry


class TestDevicePlugin:
    """Reference dpost test device plugin for plugin-loading ownership tests."""

    __test__ = False

    def __init__(self) -> None:
        self._config = build_config()
        self._file_processor = TestFileProcessor(device_config=self._config)

    def get_config(self) -> DeviceConfig:
        return self._config

    def get_file_processor(self) -> TestFileProcessor:
        return self._file_processor


@hookimpl
def register_device_plugins(registry: "DevicePluginRegistry") -> None:
    """Register the reference dpost test device plugin."""
    registry.register("test_device", TestDevicePlugin)
