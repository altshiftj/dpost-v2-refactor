from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

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


def _processing_context_for(source_path: str) -> ProcessingContext:
    return ProcessingContext.for_candidate(
        runtime_context=_runtime_context(),
        candidate_event={
            "source_path": source_path,
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


def test_host_can_activate_and_create_processors_for_all_mapped_device_plugins(
    tmp_path,
) -> None:
    discovered = discover_from_namespaces()
    host = PluginHost(discovered.descriptors)
    host.activate_profile(profile="prod", known_profiles={"prod"})

    assert host.get_device_plugins() == EXPECTED_DEVICE_PLUGIN_IDS

    descriptors = {
        descriptor.plugin_id: descriptor for descriptor in discovered.descriptors
    }
    for plugin_id in EXPECTED_DEVICE_PLUGIN_IDS:
        validate_settings = descriptors[plugin_id].module_exports["validate_settings"]
        settings = validate_settings({})
        processor = host.create_device_processor(plugin_id, settings={})
        if plugin_id == "sem_phenomxl2":
            sample_source = str(tmp_path / "sem_phenomxl21.tiff")
            result = processor.process(
                processor.prepare({"source_path": sample_source}),
                _processing_context_for(sample_source),
            )
            assert processor.can_process({"source_path": sample_source}) is True
            assert result.final_path.endswith("sem_phenomxl2.tiff")
            assert result.datatype == "img"
            continue

        if plugin_id == "utm_zwick":
            zs2_path = tmp_path / "utm_zwick-sample.zs2"
            xlsx_path = tmp_path / "utm_zwick-sample.xlsx"
            zs2_path.write_text("raw", encoding="utf-8")
            xlsx_path.write_text("results", encoding="utf-8")
            processor.prepare({"source_path": str(zs2_path)})
            prepared = processor.prepare({"source_path": str(xlsx_path)})
            assert processor.can_process(prepared) is True
            result = processor.process(
                prepared, _processing_context_for(str(xlsx_path))
            )
            assert result.final_path == str(xlsx_path)
            assert result.datatype == "xlsx"
            assert result.force_paths == (str(zs2_path), str(xlsx_path))
            continue

        if plugin_id == "psa_horiba":
            bucket_ngb = tmp_path / "bucket_a.ngb"
            bucket_csv = tmp_path / "bucket_a.csv"
            sentinel_csv = tmp_path / "sentinel.csv"
            sentinel_ngb = tmp_path / "sentinel.ngb"
            bucket_ngb.write_text("ngb-a", encoding="utf-8")
            bucket_csv.write_text(
                "Probenname;Sample Batch\nX(mm);Value\n",
                encoding="utf-8",
            )
            sentinel_csv.write_text(
                "Probenname;Final Sample\nX(mm);Value\n",
                encoding="utf-8",
            )
            sentinel_ngb.write_text("ngb-final", encoding="utf-8")
            processor.prepare({"source_path": str(bucket_ngb)})
            processor.prepare({"source_path": str(bucket_csv)})
            processor.prepare({"source_path": str(sentinel_csv)})
            prepared = processor.prepare({"source_path": str(sentinel_ngb)})
            assert processor.can_process(prepared) is True
            result = processor.process(
                prepared,
                _processing_context_for(str(sentinel_ngb)),
            )
            assert Path(result.final_path).name == "Final Sample-01.csv"
            assert result.datatype == "psa"
            assert {Path(path).name for path in result.force_paths} == {
                "Final Sample-01.zip",
                "Final Sample-02.csv",
                "Final Sample-02.zip",
            }
            continue

        extension = settings.source_extensions[0]
        sample_source = f"D:/incoming/{plugin_id}{extension}"
        assert processor.can_process({"source_path": sample_source})

        result = processor.process(
            {"source_path": sample_source}, _processing_context()
        )
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
