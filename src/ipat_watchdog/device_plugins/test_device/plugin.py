from __future__ import annotations

from ipat_watchdog.device_plugins.device_plugin import DevicePlugin
from ipat_watchdog.device_plugins.test_device.settings import build_config
from ipat_watchdog.device_plugins.test_device.file_processor import TestFileProcessor
from ipat_watchdog.core.config import DeviceConfig


class TestDevicePlugin(DevicePlugin):
    """Test device plugin for unit and integration testing."""

    def __init__(self) -> None:
        self._config = build_config()
        self._file_processor = TestFileProcessor()

    def get_config(self) -> DeviceConfig:
        return self._config

    def get_file_processor(self) -> TestFileProcessor:
        return self._file_processor
