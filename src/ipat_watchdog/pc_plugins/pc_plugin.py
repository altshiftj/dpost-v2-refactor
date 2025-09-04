from abc import ABC, abstractmethod
from ipat_watchdog.core.config.pc_settings import PCSettings

class PCPlugin(ABC):
    @abstractmethod
    def get_settings(self) -> PCSettings:
        pass
