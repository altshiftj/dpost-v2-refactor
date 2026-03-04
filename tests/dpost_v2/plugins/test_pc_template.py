from __future__ import annotations

import pytest

from dpost_v2.application.contracts.plugin_contracts import PLUGIN_CONTRACT_VERSION
from dpost_v2.plugins.pcs._pc_template.plugin import (
    capabilities,
    create_sync_adapter,
    metadata,
    prepare_sync_payload,
)
from dpost_v2.plugins.pcs._pc_template.settings import (
    PcPluginSettingsModeError,
    validate_pc_plugin_settings,
)


def test_pc_template_plugin_exports_contract_metadata_and_capabilities() -> None:
    plugin_metadata = metadata()
    plugin_capabilities = capabilities()

    assert plugin_metadata.family == "pc"
    assert plugin_metadata.contract_version == PLUGIN_CONTRACT_VERSION
    assert plugin_capabilities.supports_sync is True
    assert plugin_capabilities.can_process is False


def test_pc_template_settings_apply_defaults_and_redact_secrets() -> None:
    settings = validate_pc_plugin_settings({"api_token": "secret-token"})
    adapter = create_sync_adapter({"api_token": "secret-token"})

    assert settings.endpoint == "https://example.invalid/api"
    assert settings.upload_mode == "immediate"
    assert settings.redacted().get("api_token") == "***"
    assert adapter["upload_mode"] == "immediate"


def test_pc_template_settings_reject_invalid_upload_mode() -> None:
    with pytest.raises(PcPluginSettingsModeError, match="upload_mode"):
        validate_pc_plugin_settings({"upload_mode": "invalid"})


def test_pc_template_prepare_sync_payload_requires_record_id() -> None:
    with pytest.raises(ValueError, match="record_id"):
        prepare_sync_payload({}, context=None)  # type: ignore[arg-type]
