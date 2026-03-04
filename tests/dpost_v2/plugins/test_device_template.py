from __future__ import annotations

from datetime import UTC, datetime

import pytest

from dpost_v2.application.contracts.context import ProcessingContext, RuntimeContext
from dpost_v2.application.contracts.plugin_contracts import PLUGIN_CONTRACT_VERSION
from dpost_v2.plugins.devices._device_template.plugin import (
    capabilities,
    create_processor,
    metadata,
    validate_settings,
)
from dpost_v2.plugins.devices._device_template.settings import (
    DevicePluginSettingsUnknownKeyError,
    validate_device_plugin_settings,
)


def _runtime_context() -> RuntimeContext:
    return RuntimeContext.from_settings(
        settings={
            "mode": "headless",
            "profile": "prod",
            "session_id": "session-template",
            "event_id": "event-template",
            "trace_id": "trace-template",
        },
        dependency_ids={"clock": "clock-1", "ui": "ui-1", "sync": "sync-1"},
    )


def _processing_context() -> ProcessingContext:
    return ProcessingContext.for_candidate(
        runtime_context=_runtime_context(),
        candidate_event={
            "source_path": "D:/incoming/sample.csv",
            "event_type": "created",
            "observed_at": datetime(2026, 3, 4, 11, 0, tzinfo=UTC),
        },
    )


def test_device_template_plugin_exports_contract_metadata_and_capabilities() -> None:
    plugin_metadata = metadata()
    plugin_capabilities = capabilities()

    assert plugin_metadata.family == "device"
    assert plugin_metadata.contract_version == PLUGIN_CONTRACT_VERSION
    assert plugin_capabilities.can_process is True
    assert plugin_capabilities.supports_sync is False


def test_device_template_settings_apply_defaults() -> None:
    settings = validate_device_plugin_settings({})

    assert settings.plugin_id == "device.template"
    assert settings.source_extensions == (".dat", ".txt")
    assert settings.strict_unknown_keys is True


def test_device_template_settings_reject_unknown_keys_in_strict_mode() -> None:
    with pytest.raises(DevicePluginSettingsUnknownKeyError, match="mystery"):
        validate_device_plugin_settings({"mystery": True})


def test_device_template_processor_prepare_and_process_are_deterministic() -> None:
    normalized = validate_settings(
        {"plugin_id": "device.template", "source_extensions": [".csv"]}
    )
    processor = create_processor(
        {"plugin_id": "device.template", "source_extensions": [".csv"]}
    )

    prepared = processor.prepare({"source_path": "D:/incoming/sample.csv"})
    result = processor.process(prepared, _processing_context())

    assert normalized.plugin_id == "device.template"
    assert prepared["source_path"] == "D:/incoming/sample.csv"
    assert result.final_path == "D:/incoming/sample.csv"
