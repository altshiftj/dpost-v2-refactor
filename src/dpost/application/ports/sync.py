"""Application sync adapter port contract."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class SyncAdapterPort(Protocol):
    """Define the sync adapter behavior required by application services."""

    def sync_record_to_database(self, local_record: object) -> bool:
        """Synchronize a local record and return whether uploads remain pending."""
