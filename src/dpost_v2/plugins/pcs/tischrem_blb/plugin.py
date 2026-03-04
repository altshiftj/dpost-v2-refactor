"""Concrete V2 tischrem_blb PC plugin adapter exports."""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Mapping

from dpost_v2.application.contracts.context import RuntimeContext
from dpost_v2.application.contracts.plugin_contracts import (
    PLUGIN_CONTRACT_VERSION,
    PluginCapabilities,
    PluginMetadata,
)
from dpost_v2.plugins.pcs.tischrem_blb.settings import (
    PcPluginSettings,
    validate_tischrem_blb_settings,
)


def metadata() -> PluginMetadata:
    """Return stable metadata for concrete tischrem_blb plugin."""
    return PluginMetadata(
        plugin_id="tischrem_blb",
        family="pc",
        version="1.0.0",
        contract_version=PLUGIN_CONTRACT_VERSION,
        supported_profiles=("prod",),
    )


def capabilities() -> PluginCapabilities:
    """Return capability flags for concrete tischrem_blb plugin."""
    return PluginCapabilities(
        can_process=False,
        supports_preprocess=False,
        supports_batch=False,
        supports_sync=True,
    )


def validate_settings(raw_settings: Mapping[str, Any]) -> PcPluginSettings:
    """Validate and normalize tischrem_blb settings payload."""
    return validate_tischrem_blb_settings(raw_settings)


def create_sync_adapter(settings: Mapping[str, Any]) -> Mapping[str, Any]:
    """Create deterministic sync-adapter payload for tischrem_blb plugin."""
    normalized = validate_settings(settings)
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
    """Prepare sync payload for tischrem_blb plugin."""
    _ = context
    record_id = record.get("record_id")
    if not isinstance(record_id, str) or not record_id.strip():
        raise ValueError("record_id is required")
    return MappingProxyType(
        {"record_id": record_id.strip(), "plugin_id": "tischrem_blb"}
    )


def on_shutdown() -> None:
    """Run the optional lifecycle shutdown hook."""
