# src/ipat_watchdog/plugins/sem_tischrem_blb/plugin.py
from __future__ import annotations

from ipat_watchdog.device_plugins.device_plugin import DevicePlugin
from ipat_watchdog.device_plugins.psa_horibalinks_blb.settings import HoribaLinksSettings
from ipat_watchdog.device_plugins.psa_horibalinks_blb.file_processor import FileProcessorHoribaLinks
from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS
from ipat_watchdog.core.config.settings_base import BaseSettings

class HoribaLinksPlugin(DevicePlugin):
    """Registers the Horiba Partica LA-960 device with the Watchdog app."""

    def __init__(self) -> None:
        self._settings = HoribaLinksSettings()
        self._processor = FileProcessorHoribaLinks()

    # ---- DevicePlugin contract ---------------------------------------------

    def get_settings(self) -> BaseSettings:
        return self._settings

    def get_file_processor(self) -> FileProcessorABS:
        return self._processor
