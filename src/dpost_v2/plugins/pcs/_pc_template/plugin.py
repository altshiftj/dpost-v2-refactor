"""Template PC plugin adapter exports for host/discovery integration."""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Mapping

from dpost_v2.application.contracts.context import RuntimeContext
from dpost_v2.application.contracts.plugin_contracts import (
    PLUGIN_CONTRACT_VERSION,
    PluginCapabilities,
    PluginMetadata,
)
from dpost_v2.plugins.pcs._pc_template.settings import (
    PcPluginSettings,
    validate_pc_plugin_settings,
)


def metadata() -> PluginMetadata:
    """Return stable metadata for the template PC plugin."""
    return PluginMetadata(
        plugin_id="pc.template",
        family="pc",
        version="0.1.0",
        contract_version=PLUGIN_CONTRACT_VERSION,
        supported_profiles=("prod", "default"),
    )


def capabilities() -> PluginCapabilities:
    """Return explicit capability flags for template PC plugin."""
    return PluginCapabilities(
        can_process=False,
        supports_preprocess=False,
        supports_batch=False,
        supports_sync=True,
    )


def create_sync_adapter(settings: Mapping[str, Any]) -> Mapping[str, Any]:
    """Create a normalized sync adapter payload for runtime handoff."""
    normalized = validate_pc_plugin_settings(settings)
    return MappingProxyType(
        {
            "endpoint": normalized.endpoint,
            "workspace_id": normalized.workspace_id,
            "upload_mode": normalized.upload_mode,
            "api_token": normalized.api_token,
        }
    )


def prepare_sync_payload(
    record: Mapping[str, Any],
    context: RuntimeContext,
) -> Mapping[str, Any]:
    """Prepare outbound sync payload with deterministic field ordering."""
    _ = context
    record_id = record.get("record_id")
    if not isinstance(record_id, str) or not record_id.strip():
        raise ValueError("record_id is required for sync payload preparation")
    return MappingProxyType({"record_id": record_id.strip()})


def validate_settings(raw_settings: Mapping[str, Any]) -> PcPluginSettings:
    """Validate and normalize raw PC plugin settings payload."""
    return validate_pc_plugin_settings(raw_settings)


def before_sync(_context: Mapping[str, Any]) -> None:
    """Run the optional lifecycle hook before sync operations."""


def after_sync(_context: Mapping[str, Any]) -> None:
    """Run the optional lifecycle hook after sync operations."""


def on_shutdown() -> None:
    """Run the optional lifecycle hook when host shuts down."""
