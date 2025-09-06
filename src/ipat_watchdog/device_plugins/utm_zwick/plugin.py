# src/ipat_watchdog/plugins/sem_phenomxl2/plugin.py
from __future__ import annotations

from ipat_watchdog.device_plugins.device_plugin import DevicePlugin
from ipat_watchdog.device_plugins.utm_zwick.settings import SettingsZwickUTM
from ipat_watchdog.device_plugins.utm_zwick.file_processor import FileProcessorZwickUTM
from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS
from ipat_watchdog.core.config.device_settings_base import DeviceSettings

class UTMZwickPlugin(DevicePlugin):
    """Registers the Zwick UTM device with the Watchdog app."""

    def __init__(self) -> None:
        self._settings = SettingsZwickUTM()
        self._processor = FileProcessorZwickUTM()

    # ---- DevicePlugin contract ---------------------------------------------

    def get_settings(self) -> DeviceSettings:
        return self._settings

    def get_file_processor(self) -> FileProcessorABS:
        return self._processor
