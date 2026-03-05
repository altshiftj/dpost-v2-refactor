"""Application-level wiring for running the Watchdog service."""

from .bootstrap import (
    BootstrapContext,
    MissingConfiguration,
    StartupError,
    StartupSettings,
    bootstrap,
    collect_startup_settings,
)

__all__ = [
    "bootstrap",
    "collect_startup_settings",
    "BootstrapContext",
    "StartupSettings",
    "StartupError",
    "MissingConfiguration",
]
