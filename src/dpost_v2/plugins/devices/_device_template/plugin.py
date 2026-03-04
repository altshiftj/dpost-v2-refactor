"""Template device plugin adapter exports for host/discovery integration."""

from __future__ import annotations

from typing import Any, Mapping

from dpost_v2.application.contracts.plugin_contracts import (
    PLUGIN_CONTRACT_VERSION,
    PluginCapabilities,
    PluginMetadata,
)
from dpost_v2.plugins.devices._device_template.processor import TemplateDeviceProcessor
from dpost_v2.plugins.devices._device_template.settings import (
    DevicePluginSettings,
    validate_device_plugin_settings,
)


def metadata() -> PluginMetadata:
    """Return stable metadata for the template device plugin."""
    return PluginMetadata(
        plugin_id="device.template",
        family="device",
        version="0.1.0",
        contract_version=PLUGIN_CONTRACT_VERSION,
        supported_profiles=("prod", "default"),
    )


def capabilities() -> PluginCapabilities:
    """Return explicit capability flags for template device plugin."""
    return PluginCapabilities(
        can_process=True,
        supports_preprocess=False,
        supports_batch=False,
        supports_sync=False,
    )


def validate_settings(raw_settings: Mapping[str, Any]) -> DevicePluginSettings:
    """Validate and normalize raw device settings payload."""
    return validate_device_plugin_settings(raw_settings)


def create_processor(settings: Mapping[str, Any]) -> TemplateDeviceProcessor:
    """Create template processor bound to normalized settings."""
    normalized = validate_settings(settings)
    return TemplateDeviceProcessor(settings=normalized)


def on_activate(_context: Mapping[str, Any]) -> None:
    """Run the optional activation hook for host lifecycle transitions."""


def on_shutdown() -> None:
    """Run the optional shutdown hook for host lifecycle transitions."""
