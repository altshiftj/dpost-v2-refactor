"""Logging adapter boundary for canonical dpost startup paths."""

from __future__ import annotations

from ipat_watchdog.core.logging.logger import setup_logger as _legacy_setup_logger


def setup_logger(name: str):
    """Return a configured logger using the active logging backend."""
    return _legacy_setup_logger(name)
