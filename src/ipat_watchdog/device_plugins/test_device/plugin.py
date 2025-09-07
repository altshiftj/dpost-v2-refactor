# ipat_watchdog/device_plugins/test_device/plugin.py
from __future__ import annotations

from ipat_watchdog.device_plugins.device_plugin import DevicePlugin
from ipat_watchdog.device_plugins.test_device.settings import TestDeviceSettings
from ipat_watchdog.device_plugins.test_device.file_processor import TestFileProcessor


class TestDevicePlugin(DevicePlugin):
    """Test device plugin for unit and integration testing."""

    def __init__(self) -> None:
        self._settings = TestDeviceSettings()
        self._file_processor = TestFileProcessor()

    # ---- DevicePlugin contract ---------------------------------------------

    def get_settings(self) -> TestDeviceSettings:
        return self._settings

    def get_file_processor(self) -> TestFileProcessor:
        return self._file_processor
