from __future__ import annotations

from datetime import UTC, datetime

from dpost_v2.application.contracts.context import ProcessingContext, RuntimeContext
from dpost_v2.plugins.discovery import discover_from_namespaces
from dpost_v2.plugins.host import PluginHost


EXPECTED_DEVICE_PLUGIN_IDS = (
    "dsv_horiba",
    "erm_hioki",
    "extr_haake",
    "psa_horiba",
    "rhe_kinexus",
    "rmx_eirich_el1",
    "rmx_eirich_r01",
    "sem_phenomxl2",
    "test_device",
    "utm_zwick",
)
EXPECTED_PC_PLUGIN_IDS = (
    "eirich_blb",
    "haake_blb",
    "hioki_blb",
    "horiba_blb",
    "kinexus_blb",
    "test_pc",
    "tischrem_blb",
    "zwick_blb",
)


def _runtime_context() -> RuntimeContext:
    return RuntimeContext.from_settings(
        settings={
            "mode": "headless",
            "profile": "prod",
            "session_id": "session-plugin-migration",
            "event_id": "event-plugin-migration",
            "trace_id": "trace-plugin-migration",
        },
        dependency_ids={"clock": "clock-1", "ui": "ui-1", "sync": "sync-1"},
    )


def _processing_context() -> ProcessingContext:
    return ProcessingContext.for_candidate(
        runtime_context=_runtime_context(),
        candidate_event={
            "source_path": "D:/incoming/mapped-plugin-sample.csv",
            "event_type": "created",
            "observed_at": datetime(2026, 3, 4, 10, 30, tzinfo=UTC),
        },
    )


def test_namespace_discovery_includes_all_mapped_plugin_packages() -> None:
    discovered = discover_from_namespaces()
    devices = tuple(
        descriptor.plugin_id
        for descriptor in discovered.descriptors
        if descriptor.family == "device"
    )
    pcs = tuple(
        descriptor.plugin_id
        for descriptor in discovered.descriptors
        if descriptor.family == "pc"
    )

    assert devices == EXPECTED_DEVICE_PLUGIN_IDS
    assert pcs == EXPECTED_PC_PLUGIN_IDS


def test_host_can_activate_and_create_processors_for_all_mapped_device_plugins() -> None:
    discovered = discover_from_namespaces()
    host = PluginHost(discovered.descriptors)
    host.activate_profile(profile="prod", known_profiles={"prod"})

    assert host.get_device_plugins() == EXPECTED_DEVICE_PLUGIN_IDS

    descriptors = {descriptor.plugin_id: descriptor for descriptor in discovered.descriptors}
    context = _processing_context()
    for plugin_id in EXPECTED_DEVICE_PLUGIN_IDS:
        validate_settings = descriptors[plugin_id].module_exports["validate_settings"]
        settings = validate_settings({})
        extension = settings.source_extensions[0]
        sample_source = f"D:/incoming/{plugin_id}{extension}"

        processor = host.create_device_processor(plugin_id, settings={})
        assert processor.can_process({"source_path": sample_source})

        result = processor.process({"source_path": sample_source}, context)
        assert result.final_path == sample_source
        assert result.datatype.startswith(f"{plugin_id}/")


def test_mapped_pc_plugins_expose_sync_adapter_and_payload_contracts() -> None:
    discovered = discover_from_namespaces()
    runtime_context = _runtime_context()
    descriptors = {
        descriptor.plugin_id: descriptor
        for descriptor in discovered.descriptors
        if descriptor.family == "pc"
    }

    assert tuple(descriptors) == EXPECTED_PC_PLUGIN_IDS
    for plugin_id in EXPECTED_PC_PLUGIN_IDS:
        descriptor = descriptors[plugin_id]
        assert descriptor.capabilities.can_process is False
        assert descriptor.capabilities.supports_sync is True

        sync_adapter = descriptor.module_exports["create_sync_adapter"]({})
        payload = descriptor.module_exports["prepare_sync_payload"](
            {"record_id": "record-1"},
            runtime_context,
        )

        assert sync_adapter is not None
        assert payload["record_id"] == "record-1"
