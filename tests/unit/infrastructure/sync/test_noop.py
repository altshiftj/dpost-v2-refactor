"""Unit coverage for no-op sync adapter behavior."""

from __future__ import annotations

from dpost.infrastructure.sync.noop import NoopSyncAdapter


def test_noop_sync_adapter_always_returns_false() -> None:
    """Return ``False`` for all sync attempts without side effects."""
    adapter = NoopSyncAdapter()
    assert adapter.sync_record_to_database(local_record=object()) is False
