# src/ipat_watchdog/device_plugins/dsv_horiba/plugin.py
from __future__ import annotations

from ipat_watchdog.device_plugins.device_plugin import DevicePlugin
from ipat_watchdog.device_plugins.dsv_horiba.settings import SettingsDSVHoriba
from ipat_watchdog.device_plugins.dsv_horiba.file_processor import FileProcessorDSVHoriba
from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS
from ipat_watchdog.core.config.device_settings_base import DeviceSettings


class DSVHoribaPlugin(DevicePlugin):
    """Registers the Horiba Dissolver device with the Watchdog app."""

    def __init__(self) -> None:
        self._settings = SettingsDSVHoriba()
        self._processor = FileProcessorDSVHoriba()

    # ---- DevicePlugin contract ---------------------------------------------

    def get_settings(self) -> DeviceSettings:
        return self._settings

    def get_file_processor(self) -> FileProcessorABS:
        return self._processor
