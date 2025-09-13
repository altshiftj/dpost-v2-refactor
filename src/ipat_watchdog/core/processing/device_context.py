"""
Device context manager that sets/clears the current device on SettingsManager.
"""
from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Optional


class DeviceContext(AbstractContextManager):
    """Context manager that sets the current device and clears it on exit."""

    def __init__(self, settings_manager, device_settings) -> None:
        self._settings_manager = settings_manager
        self._device_settings = device_settings

    def __enter__(self):
        if self._device_settings is not None:
            self._settings_manager.set_current_device(self._device_settings)
        return self._device_settings

    def __exit__(self, exc_type, exc, tb):
        try:
            self._settings_manager.set_current_device(None)
        except Exception:
            pass
        return False

    @classmethod
    def from_file(cls, settings_manager, src_path: str):
        device_settings = settings_manager.select_device_for_file(src_path)
        return cls(settings_manager, device_settings)
