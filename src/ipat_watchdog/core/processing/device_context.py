"""Lightweight context manager that binds the active device for a processing run."""
from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Optional

from ipat_watchdog.core.config.device_settings_base import DeviceSettings
from ipat_watchdog.core.config.settings_store import SettingsManager


@dataclass
class DeviceContext(AbstractContextManager[Optional[DeviceSettings]]):
    """Push a device onto the SettingsManager stack for the duration of the block."""

    settings_manager: SettingsManager
    device_settings: Optional[DeviceSettings]

    def __enter__(self) -> Optional[DeviceSettings]:  # noqa: D401
        if self.device_settings is not None:
            self.settings_manager.set_current_device(self.device_settings)
        return self.device_settings

    def __exit__(self, exc_type, exc, tb) -> bool:  # noqa: D401
        try:
            self.settings_manager.set_current_device(None)
        except Exception:
            # Reset failures must never cascade onto the caller; log upstream.
            pass
        return False

    @classmethod
    def from_file(cls, settings_manager: SettingsManager, src_path: str) -> "DeviceContext":
        device_settings = settings_manager.select_device_for_file(src_path)
        return cls(settings_manager=settings_manager, device_settings=device_settings)
