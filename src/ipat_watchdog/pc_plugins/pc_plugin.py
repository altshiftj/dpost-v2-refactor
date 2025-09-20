from abc import ABC, abstractmethod

from ipat_watchdog.core.config import PCConfig


class PCPlugin(ABC):
    """Base interface for PC-level configuration plugins."""

    @abstractmethod
    def get_config(self) -> PCConfig:
        """Return the configuration describing this PC environment."""
        raise NotImplementedError
