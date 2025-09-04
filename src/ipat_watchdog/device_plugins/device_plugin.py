from abc import ABC, abstractmethod
from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS
from ipat_watchdog.core.config.device_settings_base import DeviceSettings

class DevicePlugin(ABC):
    @abstractmethod
    def get_settings(self) -> DeviceSettings:
        pass

    @abstractmethod
    def get_file_processor(self) -> FileProcessorABS:
        pass
