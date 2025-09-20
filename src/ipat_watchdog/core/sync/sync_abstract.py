from __future__ import annotations

from abc import ABC, abstractmethod

from ipat_watchdog.core.interactions import UserInteractionPort
from ipat_watchdog.core.records.local_record import LocalRecord


class ISyncManager(ABC):
    """Interface for managing synchronization operations between local records and the database."""

    def __init__(self, interactions: UserInteractionPort):
        self.interactions = interactions

    @abstractmethod
    def sync_record_to_database(self, local_record: LocalRecord):
        """Synchronize a local record to the database."""
        raise NotImplementedError
