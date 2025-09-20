"""Runtime helpers for initialising and accessing the global configuration service."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterable

from .schema import DeviceConfig, PCConfig
from .service import ConfigService, ActiveConfig

__all__ = [
    "init_config",
    "set_service",
    "get_service",
    "reset_service",
    "current",
    "activate_device",
]


_config_service: ConfigService | None = None


def init_config(pc: PCConfig, devices: Iterable[DeviceConfig] | None = None) -> ConfigService:
    """Create and register a ConfigService instance."""
    service = ConfigService(pc, devices)
    set_service(service)
    return service


def set_service(service: ConfigService) -> None:
    global _config_service
    _config_service = service


def get_service() -> ConfigService:
    if _config_service is None:
        raise RuntimeError("Configuration service has not been initialised")
    return _config_service


def reset_service() -> None:
    global _config_service
    _config_service = None


def current() -> ActiveConfig:
    return get_service().current


@contextmanager
def activate_device(device: DeviceConfig | str | None):
    service = get_service()
    with service.activate_device(device) as resolved:
        yield resolved
