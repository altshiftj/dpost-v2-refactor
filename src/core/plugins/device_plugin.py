from abc import ABC, abstractmethod
from src.core.processing.file_processor_abstract import FileProcessorBase
from src.core.config.settings_base import BaseSettings

class DevicePlugin(ABC):
    @abstractmethod
    def get_settings(self) -> BaseSettings:
        pass

    @abstractmethod
    def get_file_processor(self) -> FileProcessorBase:
        pass
