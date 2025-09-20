from abc import ABC, abstractmethod

from ipat_watchdog.core.config import DeviceConfig
from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS


class DevicePlugin(ABC):
    """Base interface for device-level plugins."""

    @abstractmethod
    def get_config(self) -> DeviceConfig:
        """Return the configuration describing this device."""
        raise NotImplementedError

    @abstractmethod
    def get_file_processor(self) -> FileProcessorABS:
        """Return the file processor implementation for this device."""
        raise NotImplementedError
