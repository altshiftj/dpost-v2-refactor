"""Composition root for dpost startup wiring."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from dpost.application.ports import SyncAdapterPort
from dpost.infrastructure.sync import NoopSyncAdapter

if TYPE_CHECKING:
    from ipat_watchdog.core.app.bootstrap import BootstrapContext


def select_sync_adapter(adapter_name: str | None = None) -> SyncAdapterPort:
    """Return the selected sync adapter implementation."""
    selected_name = (
        (adapter_name or os.getenv("DPOST_SYNC_ADAPTER") or "noop").strip().lower()
    )

    if selected_name == "noop":
        return NoopSyncAdapter()

    from ipat_watchdog.core.app.bootstrap import StartupError

    raise StartupError(
        f"Unknown sync adapter '{selected_name}'. Available adapters: noop."
    )


def compose_bootstrap() -> "BootstrapContext":
    """Build and return the runtime context for dpost.

    This temporary implementation delegates to the existing ipat_watchdog
    bootstrap path while migration is in progress.
    """
    from ipat_watchdog.core.app.bootstrap import bootstrap as legacy_bootstrap

    return legacy_bootstrap()
