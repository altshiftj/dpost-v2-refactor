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

    if selected_name == "kadi":
        try:
            from dpost.infrastructure.sync.kadi import KadiSyncAdapter

            return KadiSyncAdapter()
        except ModuleNotFoundError as exc:
            from ipat_watchdog.core.app.bootstrap import StartupError

            raise StartupError(
                "Kadi sync adapter requires optional dependency 'kadi_apy'."
            ) from exc

    from ipat_watchdog.core.app.bootstrap import StartupError

    raise StartupError(
        f"Unknown sync adapter '{selected_name}'. Available adapters: noop, kadi."
    )


def compose_bootstrap() -> "BootstrapContext":
    """Build and return the runtime context for dpost.

    This temporary implementation delegates to the existing ipat_watchdog
    bootstrap path while migration is in progress.
    """
    from ipat_watchdog.core.app.bootstrap import bootstrap as legacy_bootstrap

    sync_adapter = select_sync_adapter()

    def sync_manager_factory(_interactions: object) -> SyncAdapterPort:
        return sync_adapter

    return legacy_bootstrap(sync_manager_factory=sync_manager_factory)
