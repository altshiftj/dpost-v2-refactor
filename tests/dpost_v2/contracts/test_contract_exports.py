"""Cross-module contract surface tests for V2 contract package exports."""

from __future__ import annotations

from datetime import UTC, datetime

from dpost_v2.application import contracts


def test_contracts_package_exports_expected_symbols() -> None:
    expected_symbols = {
        "RuntimeContext",
        "ProcessingContext",
        "validate_runtime_context",
        "validate_processing_context",
        "EventKind",
        "EventSeverity",
        "EventStage",
        "BaseEvent",
        "IngestionDeferred",
        "event_from_outcome",
        "to_payload",
        "UiPort",
        "EventPort",
        "RecordStorePort",
        "FileOpsPort",
        "SyncPort",
        "PluginHostPort",
        "ClockPort",
        "FilesystemPort",
        "validate_port_bindings",
        "DevicePluginContract",
        "PcPluginContract",
        "ProcessorContract",
        "PluginMetadata",
        "PluginCapabilities",
        "ProcessorDescriptor",
        "ProcessorResult",
        "validate_plugin_contract",
        "validate_processor_result",
        "is_contract_version_compatible",
        "PLUGIN_CONTRACT_VERSION",
    }

    assert expected_symbols.issubset(set(contracts.__all__))
    for symbol in expected_symbols:
        assert hasattr(contracts, symbol)


def test_contracts_exports_support_end_to_end_event_creation() -> None:
    runtime_context = contracts.RuntimeContext.from_settings(
        settings={
            "mode": "headless",
            "profile": "default",
            "session_id": "session-1",
            "event_id": "runtime-event-1",
            "trace_id": "trace-1",
        },
        dependency_ids={"clock": "clock-1", "ui": "ui-1", "sync": "sync-1"},
    )
    processing_context = contracts.ProcessingContext.for_candidate(
        runtime_context=runtime_context,
        candidate_event={
            "source_path": "D:/incoming/file.tif",
            "event_type": "created",
            "observed_at": datetime(2026, 3, 4, 13, 0, tzinfo=UTC),
            "event_id": "evt-500",
            "trace_id": "trace-500",
        },
    )

    event = contracts.event_from_outcome(
        {
            "status": "succeeded",
            "candidate_id": "cand-500",
            "occurred_at": datetime(2026, 3, 4, 13, 1, tzinfo=UTC),
        },
        processing_context,
    )
    payload = contracts.to_payload(event)

    assert payload["kind"] == contracts.EventKind.INGESTION_SUCCEEDED.value
    assert payload["payload"] == {"candidate_id": "cand-500"}
