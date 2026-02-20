"""Runtime bootstrap bridge used by dpost composition and entrypoints."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ipat_watchdog.core.app.bootstrap import BootstrapContext


def _bootstrap_module() -> Any:
    """Return the legacy bootstrap module via lazy import."""
    return importlib.import_module("ipat_watchdog.core.app.bootstrap")


_bootstrap = _bootstrap_module()
StartupError = _bootstrap.StartupError
MissingConfiguration = _bootstrap.MissingConfiguration


def bootstrap_runtime(**kwargs: object) -> "BootstrapContext":
    """Build and return a runtime context from startup wiring arguments.

    Resolve the bootstrap call from the module at runtime so tests can
    monkeypatch `ipat_watchdog.core.app.bootstrap.bootstrap` reliably.
    """
    return _bootstrap_module().bootstrap(**kwargs)


def collect_startup_settings(*args: object, **kwargs: object) -> Any:
    """Delegate startup settings collection to the current bootstrap module."""
    return _bootstrap_module().collect_startup_settings(*args, **kwargs)


def build_startup_settings(**kwargs: object) -> Any:
    """Construct startup settings using the current bootstrap module class."""
    return _bootstrap_module().StartupSettings(**kwargs)


def startup_error(message: str) -> Exception:
    """Create a startup error instance from the current bootstrap module."""
    return _bootstrap_module().StartupError(message)


__all__ = [
    "MissingConfiguration",
    "StartupError",
    "build_startup_settings",
    "bootstrap_runtime",
    "collect_startup_settings",
    "startup_error",
]
