"""Concrete V2 rhe_kinexus device plugin adapter exports."""

from __future__ import annotations

from typing import Any, Mapping

from dpost_v2.application.contracts.plugin_contracts import (
    PLUGIN_CONTRACT_VERSION,
    PluginCapabilities,
    PluginMetadata,
)
from dpost_v2.plugins.devices.rhe_kinexus.processor import DeviceProcessor
from dpost_v2.plugins.devices.rhe_kinexus.settings import (
    DevicePluginSettings,
    validate_rhe_kinexus_settings,
)


def metadata() -> PluginMetadata:
    """Return stable metadata for concrete rhe_kinexus plugin."""
    return PluginMetadata(
        plugin_id="rhe_kinexus",
        family="device",
        version="1.0.0",
        contract_version=PLUGIN_CONTRACT_VERSION,
        supported_profiles=("prod",),
    )


def capabilities() -> PluginCapabilities:
    """Return capability flags for concrete rhe_kinexus plugin."""
    return PluginCapabilities(
        can_process=True,
        supports_preprocess=False,
        supports_batch=False,
        supports_sync=False,
    )


def validate_settings(raw_settings: Mapping[str, Any]) -> DevicePluginSettings:
    """Validate and normalize rhe_kinexus settings payload."""
    return validate_rhe_kinexus_settings(raw_settings)


def create_processor(settings: Mapping[str, Any]) -> DeviceProcessor:
    """Create the rhe_kinexus processor from normalized settings."""
    normalized = validate_settings(settings)
    return DeviceProcessor(settings=normalized)


def on_activate(_context: Mapping[str, Any]) -> None:
    """Run the optional lifecycle activation hook."""


def on_shutdown() -> None:
    """Run the optional lifecycle shutdown hook."""
