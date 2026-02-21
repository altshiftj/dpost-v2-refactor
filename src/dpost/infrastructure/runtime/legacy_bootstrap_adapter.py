"""Legacy bootstrap adapter used by the dpost runtime bootstrap boundary."""

from __future__ import annotations

import importlib
from typing import Any

_LEGACY_BOOTSTRAP_MODULE = "ipat_watchdog.core.app.bootstrap"


def _bootstrap_module() -> Any:
    """Return the current legacy bootstrap module instance."""
    return importlib.import_module(_LEGACY_BOOTSTRAP_MODULE)


def bootstrap(**kwargs: object) -> Any:
    """Delegate bootstrap execution to the legacy runtime module."""
    return _bootstrap_module().bootstrap(**kwargs)


def collect_startup_settings(*args: object, **kwargs: object) -> Any:
    """Delegate startup settings collection to the legacy runtime module."""
    return _bootstrap_module().collect_startup_settings(*args, **kwargs)


def startup_error(message: str) -> Exception:
    """Return a startup error instance from the legacy runtime module."""
    return startup_error_type()(message)


def startup_error_type() -> type[Exception]:
    """Return the startup error class from the legacy runtime module."""
    return _bootstrap_module().StartupError


def missing_configuration_type() -> type[Exception]:
    """Return the missing-configuration class from the legacy runtime module."""
    return _bootstrap_module().MissingConfiguration
