"""Reference no-op sync adapter used for framework validation paths."""

from __future__ import annotations

from dpost.application.ports import SyncAdapterPort


class NoopSyncAdapter(SyncAdapterPort):
    """Sync adapter that intentionally performs no backend operations."""

    def sync_record_to_database(self, local_record: object) -> bool:
        """No-op sync implementation used for local/headless test paths."""
        return False
