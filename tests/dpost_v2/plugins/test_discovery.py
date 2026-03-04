from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from types import ModuleType
from typing import Any, Callable

import pytest

from dpost_v2.application.contracts.context import ProcessingContext, RuntimeContext
from dpost_v2.application.contracts.plugin_contracts import (
    PLUGIN_CONTRACT_VERSION,
    ProcessorResult,
)
from dpost_v2.plugins.discovery import (
    PluginDiscoveryDuplicateIdError,
    PluginDiscoveryFamilyError,
    discover_plugins,
)


@dataclass
class _Processor:
    marker: str = "ok"

    def can_process(self, candidate: dict[str, Any]) -> bool:
        return bool(candidate.get("source_path"))

    def process(
        self,
        candidate: dict[str, Any],
        context: ProcessingContext,
    ) -> ProcessorResult:
        _ = context
        return ProcessorResult(
            final_path=str(candidate.get("source_path", "D:/processed/output.dat")),
            datatype="text/plain",
        )


def _runtime_context() -> RuntimeContext:
    return RuntimeContext.from_settings(
        settings={
            "mode": "headless",
            "profile": "prod",
            "session_id": "session-1",
            "event_id": "event-1",
            "trace_id": "trace-1",
        },
        dependency_ids={"clock": "clock-1", "ui": "ui-1", "sync": "sync-1"},
    )


def _processing_context() -> ProcessingContext:
    return ProcessingContext.for_candidate(
        runtime_context=_runtime_context(),
        candidate_event={
            "source_path": "D:/incoming/input.txt",
            "event_type": "created",
            "observed_at": datetime(2026, 3, 4, 10, 0, tzinfo=UTC),
        },
    )


def _mapping_importer(mapping: dict[str, object]) -> Callable[[str], object]:
    def _import(module_name: str) -> object:
        if module_name in mapping:
            return mapping[module_name]
        raise ModuleNotFoundError(module_name)

    return _import


def _build_device_module(
    *,
    module_name: str,
    plugin_id: str,
    profiles: tuple[str, ...] = ("prod",),
) -> ModuleType:
    module = ModuleType(module_name)

    def metadata() -> dict[str, object]:
        return {
            "plugin_id": plugin_id,
            "family": "device",
            "version": "1.0.0",
            "contract_version": PLUGIN_CONTRACT_VERSION,
            "supported_profiles": profiles,
        }

    def capabilities() -> dict[str, bool]:
        return {
            "can_process": True,
            "supports_preprocess": False,
            "supports_batch": False,
            "supports_sync": False,
        }

    def create_processor(_settings: dict[str, Any]) -> _Processor:
        return _Processor(marker=plugin_id)

    def validate_settings(raw_settings: dict[str, Any]) -> dict[str, Any]:
        return dict(raw_settings)

    module.metadata = metadata
    module.capabilities = capabilities
    module.create_processor = create_processor
    module.validate_settings = validate_settings
    return module


def _build_pc_module(
    *,
    module_name: str,
    plugin_id: str,
    profiles: tuple[str, ...] = ("prod",),
) -> ModuleType:
    module = ModuleType(module_name)

    def metadata() -> dict[str, object]:
        return {
            "plugin_id": plugin_id,
            "family": "pc",
            "version": "2.0.0",
            "contract_version": PLUGIN_CONTRACT_VERSION,
            "supported_profiles": profiles,
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


def _build_invalid_device_module(module_name: str) -> ModuleType:
    module = ModuleType(module_name)

    def metadata() -> dict[str, object]:
        return {
            "family": "device",
            "version": "1.0.0",
            "contract_version": PLUGIN_CONTRACT_VERSION,
        }

    def capabilities() -> dict[str, bool]:
        return {
            "can_process": True,
            "supports_preprocess": False,
            "supports_batch": False,
            "supports_sync": False,
        }

    module.metadata = metadata
    module.capabilities = capabilities
    return module


def test_discover_plugins_orders_descriptors_and_fingerprints_deterministically() -> (
    None
):
    modules = {
        "plugins.pc.alpha": _build_pc_module(
            module_name="plugins.pc.alpha",
            plugin_id="pc.alpha",
        ),
        "plugins.device.beta": _build_device_module(
            module_name="plugins.device.beta",
            plugin_id="device.beta",
        ),
    }
    importer = _mapping_importer(modules)

    first = discover_plugins(
        module_names=("plugins.pc.alpha", "plugins.device.beta"),
        module_importer=importer,
    )
    second = discover_plugins(
        module_names=("plugins.device.beta", "plugins.pc.alpha"),
        module_importer=importer,
    )

    assert tuple(descriptor.plugin_id for descriptor in first.descriptors) == (
        "device.beta",
        "pc.alpha",
    )
    assert first.descriptors == second.descriptors
    assert first.fingerprint == second.fingerprint


def test_discover_plugins_collects_manifest_and_import_errors_without_aborting() -> (
    None
):
    modules = {
        "plugins.device.good": _build_device_module(
            module_name="plugins.device.good",
            plugin_id="device.good",
        ),
        "plugins.device.invalid": _build_invalid_device_module(
            "plugins.device.invalid"
        ),
    }
    importer = _mapping_importer(modules)

    discovered = discover_plugins(
        module_names=(
            "plugins.device.good",
            "plugins.device.invalid",
            "plugins.device.missing",
        ),
        module_importer=importer,
    )

    assert tuple(item.plugin_id for item in discovered.descriptors) == ("device.good",)
    assert {issue.module_name for issue in discovered.diagnostics.import_errors} == {
        "plugins.device.missing",
    }
    assert {issue.module_name for issue in discovered.diagnostics.manifest_errors} == {
        "plugins.device.invalid",
    }


def test_discover_plugins_rejects_duplicate_plugin_ids() -> None:
    modules = {
        "plugins.device.left": _build_device_module(
            module_name="plugins.device.left",
            plugin_id="device.shared",
        ),
        "plugins.device.right": _build_device_module(
            module_name="plugins.device.right",
            plugin_id="device.shared",
        ),
    }

    with pytest.raises(PluginDiscoveryDuplicateIdError, match="device.shared"):
        discover_plugins(
            module_names=("plugins.device.left", "plugins.device.right"),
            module_importer=_mapping_importer(modules),
        )


def test_discover_plugins_rejects_descriptor_family_not_in_policy() -> None:
    modules = {
        "plugins.pc.alpha": _build_pc_module(
            module_name="plugins.pc.alpha",
            plugin_id="pc.alpha",
        )
    }

    with pytest.raises(PluginDiscoveryFamilyError, match="pc.alpha"):
        discover_plugins(
            module_names=("plugins.pc.alpha",),
            module_importer=_mapping_importer(modules),
            allowed_families={"device"},
        )


def test_discovered_device_descriptor_keeps_processor_exports() -> None:
    module_name = "plugins.device.integrated"
    modules = {
        module_name: _build_device_module(
            module_name=module_name,
            plugin_id="device.integrated",
        )
    }

    discovered = discover_plugins(
        module_names=(module_name,),
        module_importer=_mapping_importer(modules),
    )

    descriptor = discovered.descriptors[0]
    processor = descriptor.module_exports["create_processor"]({"key": "value"})
    result = processor.process(
        {"source_path": "D:/incoming/file.dat"},
        _processing_context(),
    )

    assert descriptor.family == "device"
    assert result.final_path == "D:/incoming/file.dat"
