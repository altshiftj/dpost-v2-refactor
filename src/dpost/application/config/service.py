"""Services for registering configuration and resolving active device context."""

from __future__ import annotations

from contextlib import AbstractContextManager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Pattern

from .schema import (
    DeviceConfig,
    DeviceMetadata,
    NamingSettings,
    PathSettings,
    PCConfig,
    WatcherSettings,
)

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
    device: Optional[object]

    @property
    def paths(self) -> PathSettings:
        return self.pc.paths

    @property
    def naming(self) -> NamingSettings:
        return self.pc.naming

    @property
    def watcher(self) -> WatcherSettings:
        if self.device is not None:
            watcher = getattr(self.device, "watcher", None)
            if watcher is not None:
                return watcher
        return self.pc.watcher

    @property
    def session_timeout(self) -> int:
        if self.device is not None:
            session = getattr(self.device, "session", None)
            timeout = getattr(session, "timeout_seconds", None)
            if isinstance(timeout, int) and timeout >= 0:
                return timeout
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
        if self.device is None:
            return None
        metadata = getattr(self.device, "metadata", None)
        return metadata if isinstance(metadata, DeviceMetadata) else None


class ConfigService:
    """Central registry for PC/device configuration with scoped device activation."""

    def __init__(
        self, pc: PCConfig, devices: Iterable[DeviceConfig] | None = None
    ) -> None:
        self._pc = pc
        self._devices: dict[str, object] = {}
        self._active_device: ContextVar[Optional[object]] = ContextVar(
            "active_device", default=None
        )
        if devices:
            for device in devices:
                self.register_device(device)

    @property
    def pc(self) -> PCConfig:
        return self._pc

    @property
    def devices(self) -> tuple[object, ...]:
        return tuple(self._devices.values())

    def register_device(self, device: object) -> None:
        identifier = getattr(device, "identifier", None)
        if not isinstance(identifier, str) or not identifier.strip():
            raise TypeError("Device must define a non-empty 'identifier' string")
        self._devices[identifier] = device

    def get_device(self, identifier: str) -> object:
        try:
            return self._devices[identifier]
        except KeyError as exc:
            raise DeviceLookupError(identifier) from exc

    def matching_devices(self, path_like: str | Path) -> list[object]:
        target = Path(path_like)
        matches: list[object] = []
        for device in self._devices.values():
            if self._device_should_defer(device, target):
                continue
            if self._device_matches_file(device, target):
                matches.append(device)
        return matches

    def deferred_devices(self, path_like: str | Path) -> list[object]:
        target = Path(path_like)
        return [
            device
            for device in self._devices.values()
            if self._device_should_defer(device, target)
        ]

    def first_matching_device(self, path_like: str | Path) -> Optional[object]:
        for device in self._devices.values():
            if self._device_matches_file(device, path_like):
                return device
        return None

    @property
    def current(self) -> ActiveConfig:
        return ActiveConfig(pc=self._pc, device=self._active_device.get())

    def current_device(self) -> Optional[object]:
        return self._active_device.get()

    def activate_device(self, device: object | str | None) -> "_DeviceActivation":
        return _DeviceActivation(self, device)

    def set_active_device(self, device: Optional[object]) -> None:
        self._active_device.set(device)

    def clear_active_device(self) -> None:
        self._active_device.set(None)

    @staticmethod
    def _device_should_defer(device: object, path_like: str | Path) -> bool:
        resolver = getattr(device, "should_defer_dir", None)
        if callable(resolver):
            try:
                return bool(resolver(path_like))
            except Exception:
                return False
        return False

    @staticmethod
    def _device_matches_file(device: object, path_like: str | Path) -> bool:
        matcher = getattr(device, "matches_file", None)
        if callable(matcher):
            try:
                return bool(matcher(path_like))
            except Exception:
                return False
        return False


class _DeviceActivation(AbstractContextManager[Optional[object]]):
    """Context manager that manages ConfigService active device state."""

    def __init__(self, service: ConfigService, device: object | str | None) -> None:
        self._service = service
        self._device = device
        self._token: Optional[Token] = None

    def __enter__(self) -> Optional[object]:
        resolved = self._resolve_device(self._device)
        self._token = self._service._active_device.set(resolved)
        return resolved

    def __exit__(self, exc_type, exc, tb) -> bool:
        if self._token is not None:
            self._service._active_device.reset(self._token)
        return False

    def _resolve_device(self, device: object | str | None) -> Optional[object]:
        if device is None:
            return None
        if isinstance(device, str):
            return self._service.get_device(device)

        identifier = getattr(device, "identifier", None)
        if isinstance(identifier, str) and identifier in self._service._devices:
            return self._service._devices[identifier]

        if hasattr(device, "matches_file") and hasattr(device, "should_defer_dir"):
            return device

        raise DeviceLookupError(repr(device))
