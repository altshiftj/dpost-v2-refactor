"""Concrete V2 extr_haake device plugin adapter exports."""

from __future__ import annotations

from typing import Any, Mapping

from dpost_v2.application.contracts.plugin_contracts import (
    PLUGIN_CONTRACT_VERSION,
    PluginCapabilities,
    PluginMetadata,
)
from dpost_v2.plugins.devices.extr_haake.processor import DeviceProcessor
from dpost_v2.plugins.devices.extr_haake.settings import (
    DevicePluginSettings,
    validate_extr_haake_settings,
)


def metadata() -> PluginMetadata:
    """Return stable metadata for concrete extr_haake plugin."""
    return PluginMetadata(
        plugin_id="extr_haake",
        family="device",
        version="1.0.0",
        contract_version=PLUGIN_CONTRACT_VERSION,
        supported_profiles=("prod",),
    )


def capabilities() -> PluginCapabilities:
    """Return capability flags for concrete extr_haake plugin."""
    return PluginCapabilities(
        can_process=True,
        supports_preprocess=False,
        supports_batch=False,
        supports_sync=False,
    )


def validate_settings(raw_settings: Mapping[str, Any]) -> DevicePluginSettings:
    """Validate and normalize extr_haake settings payload."""
    return validate_extr_haake_settings(raw_settings)


def create_processor(settings: Mapping[str, Any]) -> DeviceProcessor:
    """Create the extr_haake processor from normalized settings."""
    normalized = validate_settings(settings)
    return DeviceProcessor(settings=normalized)


def on_activate(_context: Mapping[str, Any]) -> None:
    """Run the optional lifecycle activation hook."""


def on_shutdown() -> None:
    """Run the optional lifecycle shutdown hook."""
