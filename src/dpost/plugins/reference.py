"""Reference plugin profile definitions for framework validation flows."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PluginProfile:
    """Define a minimal plugin profile used to compose startup settings."""

    pc_name: str
    device_names: tuple[str, ...]


REFERENCE_PLUGIN_PROFILE = PluginProfile(
    pc_name="test_pc",
    device_names=("test_device",),
)
