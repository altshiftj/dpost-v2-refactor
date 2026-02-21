"""Runtime bootstrap contracts used by dpost composition and entrypoints."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from dpost.infrastructure.runtime.legacy_bootstrap_adapter import (
    bootstrap as _bootstrap,
)
from dpost.infrastructure.runtime.legacy_bootstrap_adapter import (
    collect_startup_settings as _collect_startup_settings,
)
from dpost.infrastructure.runtime.legacy_bootstrap_adapter import (
    missing_configuration_type as _missing_configuration_type,
)
from dpost.infrastructure.runtime.legacy_bootstrap_adapter import (
    startup_error as _startup_error,
)
from dpost.infrastructure.runtime.legacy_bootstrap_adapter import (
    startup_error_type as _startup_error_type,
)


@dataclass(frozen=True)
class StartupSettings:
    """Native startup settings contract for dpost runtime composition."""

    pc_name: str
    device_names: tuple[str, ...]
    prometheus_port: int = 8000
    observability_port: int = 8001
    env_source: Path | None = None


class BootstrapContext(Protocol):
    """Runtime context contract returned from bootstrap wiring."""

    settings: StartupSettings
    config_service: object
    app: object
    ui: object
    sync_manager: object
    interactions: object
    scheduler: object


def _as_startup_settings(settings: object) -> StartupSettings:
    """Return startup settings normalized to the dpost runtime contract."""
    return StartupSettings(
        pc_name=settings.pc_name,
        device_names=tuple(settings.device_names),
        prometheus_port=settings.prometheus_port,
        observability_port=settings.observability_port,
        env_source=settings.env_source,
    )


def bootstrap_runtime(**kwargs: object) -> BootstrapContext:
    """Build and return a runtime context from startup wiring arguments."""
    return _bootstrap(**kwargs)


def collect_startup_settings(*args: object, **kwargs: object) -> StartupSettings:
    """Collect startup settings and normalize them to dpost contract types."""
    resolved = _collect_startup_settings(*args, **kwargs)
    return _as_startup_settings(resolved)


def build_startup_settings(**kwargs: object) -> StartupSettings:
    """Construct startup settings using the dpost runtime contract class."""
    return StartupSettings(**kwargs)


def startup_error(message: str) -> Exception:
    """Create a startup error instance from the active bootstrap adapter."""
    return _startup_error(message)


def __getattr__(name: str) -> Any:
    """Expose bootstrap exception classes for entrypoint handling."""
    if name == "StartupError":
        return _startup_error_type()
    if name == "MissingConfiguration":
        return _missing_configuration_type()
    raise AttributeError(name)


__all__ = [
    "BootstrapContext",
    "StartupSettings",
    "build_startup_settings",
    "bootstrap_runtime",
    "collect_startup_settings",
    "startup_error",
]
