"""Services for registering configuration and resolving active device context."""

from __future__ import annotations

from contextlib import AbstractContextManager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Pattern

from .schema import DeviceConfig, PCConfig, WatcherSettings, PathSettings, NamingSettings, DeviceMetadata

__all__ = [
    "ActiveConfig",
    "ConfigService",
    "DeviceLookupError",
]


class DeviceLookupError(KeyError):
    """Raised when a device identifier is not registered with the service."""


@dataclass(slots=True)
class ActiveConfig:
    """Resolved configuration for the current execution context."""

    pc: PCConfig
    device: Optional[DeviceConfig]

    @property
    def paths(self) -> PathSettings:
        return self.pc.paths

    @property
    def naming(self) -> NamingSettings:
        return self.pc.naming

    @property
    def watcher(self) -> WatcherSettings:
        return self.device.watcher if self.device else self.pc.watcher

    @property
    def session_timeout(self) -> int:
        if self.device and self.device.session.timeout_seconds >= 0:
            return self.device.session.timeout_seconds
        return self.pc.session.timeout_seconds

    @property
    def directory_list(self) -> tuple[Path, ...]:
        return self.pc.directory_list()

    @property
    def id_separator(self) -> str:
        return self.pc.naming.id_separator

    @property
    def file_separator(self) -> str:
        return self.pc.naming.file_separator

    @property
    def filename_pattern(self) -> Pattern[str]:
        return self.pc.naming.filename_pattern

    @property
    def device_metadata(self) -> Optional[DeviceMetadata]:
        return self.device.metadata if self.device else None


class ConfigService:
    """Central registry for PC and device configuration with scoped device activation."""

    def __init__(self, pc: PCConfig, devices: Iterable[DeviceConfig] | None = None) -> None:
        self._pc = pc
        self._devices: dict[str, DeviceConfig] = {}
        self._active_device: ContextVar[Optional[DeviceConfig]] = ContextVar("active_device", default=None)
        if devices:
            for device in devices:
                self.register_device(device)

    @property
    def pc(self) -> PCConfig:
        return self._pc

    @property
    def devices(self) -> tuple[DeviceConfig, ...]:
        return tuple(self._devices.values())

    def register_device(self, device: DeviceConfig) -> None:
        self._devices[device.identifier] = device

    def get_device(self, identifier: str) -> DeviceConfig:
        try:
            return self._devices[identifier]
        except KeyError as exc:
            raise DeviceLookupError(identifier) from exc

    def matching_devices(self, path_like: str | Path) -> list[DeviceConfig]:
        return [device for device in self._devices.values() if device.matches_file(path_like)]

    def first_matching_device(self, path_like: str | Path) -> Optional[DeviceConfig]:
        for device in self._devices.values():
            if device.matches_file(path_like):
                return device
        return None

    @property
    def current(self) -> ActiveConfig:
        return ActiveConfig(pc=self._pc, device=self._active_device.get())

    def current_device(self) -> Optional[DeviceConfig]:
        return self._active_device.get()

    def activate_device(self, device: DeviceConfig | str | None) -> "_DeviceActivation":
        return _DeviceActivation(self, device)

    def set_active_device(self, device: Optional[DeviceConfig]) -> None:
        self._active_device.set(device)

    def clear_active_device(self) -> None:
        self._active_device.set(None)


class _DeviceActivation(AbstractContextManager[Optional[DeviceConfig]]):
    """Context manager that manages ConfigService active device state."""

    def __init__(self, service: ConfigService, device: DeviceConfig | str | None) -> None:
        self._service = service
        self._device = device
        self._token: Optional[Token] = None

    def __enter__(self) -> Optional[DeviceConfig]:
        resolved = self._resolve_device(self._device)
        self._token = self._service._active_device.set(resolved)
        return resolved

    def __exit__(self, exc_type, exc, tb) -> bool:
        if self._token is not None:
            self._service._active_device.reset(self._token)
        return False

    def _resolve_device(self, device: DeviceConfig | str | None) -> Optional[DeviceConfig]:
        if device is None:
            return None
        if isinstance(device, DeviceConfig):
            return device
        return self._service.get_device(device)
