"""Concrete V2 test-device plugin adapter exports."""

from __future__ import annotations

from typing import Any, Mapping

from dpost_v2.application.contracts.plugin_contracts import (
    PLUGIN_CONTRACT_VERSION,
    PluginCapabilities,
    PluginMetadata,
)
from dpost_v2.plugins.devices.test_device.processor import TestDeviceProcessor
from dpost_v2.plugins.devices.test_device.settings import (
    DevicePluginSettings,
    validate_test_device_settings,
)


def metadata() -> PluginMetadata:
    """Return stable metadata for concrete test-device plugin."""
    return PluginMetadata(
        plugin_id="test_device",
        family="device",
        version="1.0.0",
        contract_version=PLUGIN_CONTRACT_VERSION,
        supported_profiles=("prod",),
    )


def capabilities() -> PluginCapabilities:
    """Return capability flags for concrete test-device plugin."""
    return PluginCapabilities(
        can_process=True,
        supports_preprocess=False,
        supports_batch=False,
        supports_sync=False,
    )


def validate_settings(raw_settings: Mapping[str, Any]) -> DevicePluginSettings:
    """Validate and normalize test-device settings payload."""
    return validate_test_device_settings(raw_settings)


def create_processor(settings: Mapping[str, Any]) -> TestDeviceProcessor:
    """Create the test-device processor from normalized settings."""
    normalized = validate_settings(settings)
    return TestDeviceProcessor(settings=normalized)


def on_activate(_context: Mapping[str, Any]) -> None:
    """Run the optional lifecycle activation hook."""


def on_shutdown() -> None:
    """Run the optional lifecycle shutdown hook."""
