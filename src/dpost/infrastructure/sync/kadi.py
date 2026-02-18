"""Kadi sync adapter wrapper for optional dpost backend selection."""

from __future__ import annotations

from typing import TYPE_CHECKING

from dpost.application.ports import SyncAdapterPort

if TYPE_CHECKING:
    from ipat_watchdog.core.interactions import UserInteractionPort


class KadiSyncAdapter(SyncAdapterPort):
    """Lazy wrapper around the legacy Kadi sync manager implementation."""

    def __init__(self) -> None:
        """Load Kadi manager class lazily so dependency stays optional."""
        from ipat_watchdog.core.sync.sync_kadi import KadiSyncManager

        self._manager_cls = KadiSyncManager
        self._delegate = None
        self.interactions: UserInteractionPort | None = None

    def sync_record_to_database(self, local_record: object) -> bool:
        """Forward sync calls to the legacy Kadi manager."""
        if self._delegate is None:
            if self.interactions is None:
                raise RuntimeError(
                    "KadiSyncAdapter requires interactions before sync usage."
                )
            self._delegate = self._manager_cls(self.interactions)
        return bool(self._delegate.sync_record_to_database(local_record))
