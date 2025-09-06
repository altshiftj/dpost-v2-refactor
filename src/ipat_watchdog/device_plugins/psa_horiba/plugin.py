from __future__ import annotations

from ipat_watchdog.device_plugins.device_plugin import DevicePlugin
from ipat_watchdog.device_plugins.psa_horiba.settings import PSAHoribaSettings
from ipat_watchdog.device_plugins.psa_horiba.file_processor import FileProcessorPSAHoriba
from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS
from ipat_watchdog.core.config.device_settings_base import DeviceSettings

class PSAHoribaPlugin(DevicePlugin):
    """Registers the Horiba Partica LA-960 device with the Watchdog app."""

    def __init__(self) -> None:
        self._settings = PSAHoribaSettings()
        self._processor = FileProcessorPSAHoriba()

    # ---- DevicePlugin contract ---------------------------------------------

    def get_settings(self) -> DeviceSettings:
        return self._settings

    def get_file_processor(self) -> FileProcessorABS:
        return self._processor
