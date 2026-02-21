"""dpost-owned plugin protocol contracts used by loader boundaries."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class DevicePlugin(Protocol):
    """Structural contract required by dpost for device plugin instances."""

    def get_config(self) -> object:
        """Return the device configuration model."""

    def get_file_processor(self) -> object:
        """Return the processor instance used for device-specific file handling."""


@runtime_checkable
class PCPlugin(Protocol):
    """Structural contract required by dpost for PC plugin instances."""

    def get_config(self) -> object:
        """Return the PC configuration model."""
