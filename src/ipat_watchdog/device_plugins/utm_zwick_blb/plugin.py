# src/ipat_watchdog/plugins/sem_phenomxl2/plugin.py
from __future__ import annotations

from ipat_watchdog.device_plugins.device_plugin import DevicePlugin
from ipat_watchdog.device_plugins.utm_zwick_blb.settings import SettingsZwickUTM
from ipat_watchdog.device_plugins.utm_zwick_blb.file_processor import FileProcessorZwickUTM
from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS
from ipat_watchdog.core.config.settings_base import BaseSettings

class ZwickUTMPlugin(DevicePlugin):
    """Registers the Zwick UTM device with the Watchdog app."""

    def __init__(self) -> None:
        self._settings = SettingsZwickUTM()
        self._processor = FileProcessorZwickUTM()

    # ---- DevicePlugin contract ---------------------------------------------

    def get_settings(self) -> BaseSettings:
        return self._settings

    def get_file_processor(self) -> FileProcessorABS:
        return self._processor
