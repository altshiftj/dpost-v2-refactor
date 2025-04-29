from abc import ABC, abstractmethod

from ipat_watchdog.ui.ui_abstract import UserInterface
from ipat_watchdog.records.local_record import LocalRecord


class ISyncManager(ABC):
    """
    Interface for managing synchronization operations between local records and the database.

    This abstract base class defines the essential methods that any synchronization manager
    implementation must provide. It ensures consistency and standardization across different
    synchronization processes within the application.
    """

    def __init__(self, ui: UserInterface):
        self.ui = ui

    @abstractmethod
    def sync_record_to_database(self, local_record: LocalRecord):
        """
        Synchronize a local record to the database.

        Args:
            local_record (LocalRecord): The local record to synchronize.
        """
        pass
