"""Sync adapter implementations for V2 infrastructure."""

from dpost_v2.infrastructure.sync.kadi import KadiSyncAdapter
from dpost_v2.infrastructure.sync.noop import NoopSyncAdapter

__all__ = [
    "KadiSyncAdapter",
    "NoopSyncAdapter",
]
