"""Concrete V2 rmx_eirich_r01 device plugin adapter exports."""

from __future__ import annotations

from typing import Any, Mapping

from dpost_v2.application.contracts.plugin_contracts import (
    PLUGIN_CONTRACT_VERSION,
    PluginCapabilities,
    PluginMetadata,
)
from dpost_v2.plugins.devices.rmx_eirich_r01.processor import DeviceProcessor
from dpost_v2.plugins.devices.rmx_eirich_r01.settings import (
    DevicePluginSettings,
    validate_rmx_eirich_r01_settings,
)


def metadata() -> PluginMetadata:
    """Return stable metadata for concrete rmx_eirich_r01 plugin."""
    return PluginMetadata(
        plugin_id="rmx_eirich_r01",
        family="device",
        version="1.0.0",
        contract_version=PLUGIN_CONTRACT_VERSION,
        supported_profiles=("prod",),
    )


def capabilities() -> PluginCapabilities:
    """Return capability flags for concrete rmx_eirich_r01 plugin."""
    return PluginCapabilities(
        can_process=True,
        supports_preprocess=False,
        supports_batch=False,
        supports_sync=False,
    )


def validate_settings(raw_settings: Mapping[str, Any]) -> DevicePluginSettings:
    """Validate and normalize rmx_eirich_r01 settings payload."""
    return validate_rmx_eirich_r01_settings(raw_settings)


def create_processor(settings: Mapping[str, Any]) -> DeviceProcessor:
    """Create the rmx_eirich_r01 processor from normalized settings."""
    normalized = validate_settings(settings)
    return DeviceProcessor(settings=normalized)


def on_activate(_context: Mapping[str, Any]) -> None:
    """Run the optional lifecycle activation hook."""


def on_shutdown() -> None:
    """Run the optional lifecycle shutdown hook."""
