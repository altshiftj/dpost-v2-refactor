"""Composition root for dpost startup wiring."""

from __future__ import annotations

from ipat_watchdog.core.app.bootstrap import BootstrapContext
from ipat_watchdog.core.app.bootstrap import bootstrap as legacy_bootstrap


def compose_bootstrap() -> BootstrapContext:
    """Build and return the runtime context for dpost.

    This temporary implementation delegates to the existing ipat_watchdog
    bootstrap path while migration is in progress.
    """
    return legacy_bootstrap()
