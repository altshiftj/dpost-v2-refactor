from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from types import ModuleType
from typing import Any, Callable

from dpost_v2.application.contracts.context import ProcessingContext, RuntimeContext
from dpost_v2.application.contracts.plugin_contracts import (
    PLUGIN_CONTRACT_VERSION,
    ProcessorResult,
)
from dpost_v2.plugins.discovery import discover_from_namespaces, discover_plugins
from dpost_v2.plugins.host import PluginHost


@dataclass
class _Processor:
    plugin_id: str

    def can_process(self, candidate: dict[str, Any]) -> bool:
        return str(candidate.get("source_path", "")).endswith(".csv")

    def process(
        self,
        candidate: dict[str, Any],
        context: ProcessingContext,
    ) -> ProcessorResult:
        _ = context
        return ProcessorResult(
            final_path=str(candidate.get("source_path", "D:/processed/result.csv")),
            datatype=f"{self.plugin_id}/csv",
        )


def _runtime_context() -> RuntimeContext:
    return RuntimeContext.from_settings(
        settings={
            "mode": "headless",
            "profile": "prod",
            "session_id": "session-integration",
            "event_id": "event-integration",
            "trace_id": "trace-integration",
        },
        dependency_ids={"clock": "clock-1", "ui": "ui-1", "sync": "sync-1"},
    )


def _processing_context() -> ProcessingContext:
    return ProcessingContext.for_candidate(
        runtime_context=_runtime_context(),
        candidate_event={
            "source_path": "D:/incoming/device_payload.csv",
            "event_type": "created",
            "observed_at": datetime(2026, 3, 4, 10, 15, tzinfo=UTC),
        },
    )


def _mapping_importer(mapping: dict[str, object]) -> Callable[[str], object]:
    def _import(module_name: str) -> object:
        if module_name in mapping:
            return mapping[module_name]
        raise ModuleNotFoundError(module_name)

    return _import


def _build_device_module(module_name: str, plugin_id: str) -> ModuleType:
    module = ModuleType(module_name)

    def metadata() -> dict[str, object]:
        return {
            "plugin_id": plugin_id,
            "family": "device",
            "version": "1.0.0",
            "contract_version": PLUGIN_CONTRACT_VERSION,
            "supported_profiles": ("prod",),
        }

    def capabilities() -> dict[str, bool]:
        return {
            "can_process": True,
            "supports_preprocess": False,
            "supports_batch": False,
            "supports_sync": False,
        }

    def create_processor(_settings: dict[str, Any]) -> _Processor:
        return _Processor(plugin_id=plugin_id)

    def validate_settings(raw_settings: dict[str, Any]) -> dict[str, Any]:
        return dict(raw_settings)

    module.metadata = metadata
    module.capabilities = capabilities
    module.create_processor = create_processor
    module.validate_settings = validate_settings
    return module


def _build_pc_module(module_name: str, plugin_id: str) -> ModuleType:
    module = ModuleType(module_name)

    def metadata() -> dict[str, object]:
        return {
            "plugin_id": plugin_id,
            "family": "pc",
            "version": "2.1.0",
            "contract_version": PLUGIN_CONTRACT_VERSION,
            "supported_profiles": ("prod",),
        }

    def capabilities() -> dict[str, bool]:
        return {
            "can_process": False,
            "supports_preprocess": False,
            "supports_batch": False,
            "supports_sync": True,
        }

    def create_sync_adapter(_settings: dict[str, Any]) -> object:
        return object()

    def prepare_sync_payload(
        record: dict[str, Any],
        context: RuntimeContext,
    ) -> dict[str, Any]:
        _ = context
        return {"record_id": record.get("record_id")}

    module.metadata = metadata
    module.capabilities = capabilities
    module.create_sync_adapter = create_sync_adapter
    module.prepare_sync_payload = prepare_sync_payload
    return module


def _build_invalid_module(module_name: str) -> ModuleType:
    module = ModuleType(module_name)
    module.metadata = lambda: {"plugin_id": "", "family": "device"}
    module.capabilities = lambda: {}
    return module


def test_discovery_profile_selection_and_device_loading_integration() -> None:
    modules = {
        "plugins.device.alpha": _build_device_module(
            "plugins.device.alpha", "device.alpha"
        ),
        "plugins.pc.gamma": _build_pc_module("plugins.pc.gamma", "pc.gamma"),
        "plugins.device.invalid": _build_invalid_module("plugins.device.invalid"),
    }

    discovered = discover_plugins(
        module_names=(
            "plugins.device.invalid",
            "plugins.pc.gamma",
            "plugins.device.alpha",
            "plugins.device.missing",
        ),
        module_importer=_mapping_importer(modules),
    )
    host = PluginHost()
    host.register_descriptors(discovered.descriptors)
    selection = host.activate_profile(
        profile="prod",
        known_profiles={"prod"},
        deny_plugin_ids={"pc.gamma"},
    )
    processor = host.create_device_processor("device.alpha", settings={})
    output = processor.process(
        {"source_path": "D:/incoming/device_payload.csv"},
        _processing_context(),
    )

    assert {issue.module_name for issue in discovered.diagnostics.import_errors} == {
        "plugins.device.missing",
    }
    assert {issue.module_name for issue in discovered.diagnostics.manifest_errors} == {
        "plugins.device.invalid",
    }
    assert selection.selected_by_family == {"device": ("device.alpha",), "pc": ()}
    assert host.get_device_plugins() == ("device.alpha",)
    assert output.datatype == "device.alpha/csv"


def test_builtin_namespace_discovery_and_host_device_processor_integration() -> None:
    discovered = discover_from_namespaces()
    host = PluginHost()
    host.register_descriptors(discovered.descriptors)
    selection = host.activate_profile(
        profile="prod",
        known_profiles={"prod"},
        deny_plugin_ids={"test_pc"},
    )
    processor = host.create_device_processor("test_device", settings={})
    output = processor.process(
        {"source_path": "D:/incoming/device_payload.csv"},
        _processing_context(),
    )

    assert "test_device" in selection.selected_by_family["device"]
    assert "test_pc" not in selection.selected_by_family["pc"]
    assert output.datatype == "test_device/csv"
