"""Application-level wiring for running the Watchdog service."""

from .bootstrap import (
    bootstrap,
    collect_startup_settings,
    BootstrapContext,
    StartupSettings,
    StartupError,
    MissingConfiguration,
)

__all__ = [
    "bootstrap",
    "collect_startup_settings",
    "BootstrapContext",
    "StartupSettings",
    "StartupError",
    "MissingConfiguration",
]
