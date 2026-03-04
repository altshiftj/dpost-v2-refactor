"""Contract tests for V2 plugin and processor interface models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pytest

from dpost_v2.application.contracts.context import ProcessingContext, RuntimeContext
from dpost_v2.application.contracts.plugin_contracts import (
    PLUGIN_CONTRACT_VERSION,
    DevicePluginContract,
    DuplicatePluginRegistrationError,
    InvalidProcessorError,
    PcPluginContract,
    PluginCapabilities,
    PluginContractError,
    PluginMetadata,
    ProcessorContract,
    ProcessorDescriptor,
    ProcessorResult,
    is_contract_version_compatible,
    validate_plugin_contract,
    validate_processor_result,
)


def _runtime_context() -> RuntimeContext:
    return RuntimeContext.from_settings(
        settings={
            "mode": "headless",
            "profile": "default",
            "session_id": "session-1",
            "event_id": "runtime-event-1",
            "trace_id": "trace-1",
        },
        dependency_ids={"clock": "clock-1", "ui": "ui-1", "sync": "sync-1"},
    )


def _processing_context() -> ProcessingContext:
    return ProcessingContext.for_candidate(
        runtime_context=_runtime_context(),
        candidate_event={
            "source_path": "D:/incoming/file.tif",
            "event_type": "created",
            "observed_at": datetime(2026, 3, 4, 9, 30, tzinfo=UTC),
        },
    )


@dataclass
class _Processor:
    def can_process(self, candidate: dict[str, Any]) -> bool:
        return candidate.get("source_path", "").endswith(".tif")

    def process(
        self,
        candidate: dict[str, Any],
        context: ProcessingContext,
    ) -> ProcessorResult:
        return ProcessorResult(
            final_path="D:/processed/file.tif",
            datatype="image/tiff",
            force_paths=("D:/processed/aux.bin",),
        )


@dataclass
class _DevicePlugin:
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            plugin_id="device.sample",
            family="device",
            version="1.2.3",
            contract_version=PLUGIN_CONTRACT_VERSION,
            supported_profiles=("default",),
        )

    def capabilities(self) -> PluginCapabilities:
        return PluginCapabilities(
            can_process=True,
            supports_preprocess=True,
            supports_batch=False,
            supports_sync=False,
        )

    def create_processor(self, settings: dict[str, Any]) -> ProcessorContract:
        return _Processor()

    def validate_settings(self, raw_settings: dict[str, Any]) -> dict[str, Any]:
        return raw_settings


@dataclass
class _PcPlugin:
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            plugin_id="pc.sample",
            family="pc",
            version="1.0.0",
            contract_version=PLUGIN_CONTRACT_VERSION,
            supported_profiles=("default",),
        )

    def capabilities(self) -> PluginCapabilities:
        return PluginCapabilities(
            can_process=False,
            supports_preprocess=False,
            supports_batch=False,
            supports_sync=True,
        )

    def create_sync_adapter(self, settings: dict[str, Any]) -> object:
        return object()

    def prepare_sync_payload(
        self,
        record: dict[str, Any],
        context: RuntimeContext,
    ) -> dict[str, Any]:
        return {"record_id": record.get("record_id")}


def _valid_device_exports() -> dict[str, object]:
    plugin = _DevicePlugin()
    return {
        "metadata": plugin.metadata,
        "capabilities": plugin.capabilities,
        "create_processor": plugin.create_processor,
        "validate_settings": plugin.validate_settings,
    }


def _valid_pc_exports() -> dict[str, object]:
    plugin = _PcPlugin()
    return {
        "metadata": plugin.metadata,
        "capabilities": plugin.capabilities,
        "create_sync_adapter": plugin.create_sync_adapter,
        "prepare_sync_payload": plugin.prepare_sync_payload,
    }


def test_protocols_are_runtime_checkable() -> None:
    assert isinstance(_DevicePlugin(), DevicePluginContract)
    assert isinstance(_PcPlugin(), PcPluginContract)
    assert isinstance(_Processor(), ProcessorContract)


def test_validate_plugin_contract_accepts_valid_device_exports() -> None:
    metadata = validate_plugin_contract(_valid_device_exports(), seen_plugin_ids=set())

    assert metadata.plugin_id == "device.sample"
    assert metadata.family == "device"
    assert metadata.contract_version == PLUGIN_CONTRACT_VERSION


def test_validate_plugin_contract_accepts_valid_pc_exports() -> None:
    metadata = validate_plugin_contract(_valid_pc_exports(), seen_plugin_ids=set())

    assert metadata.plugin_id == "pc.sample"
    assert metadata.family == "pc"
    assert metadata.contract_version == PLUGIN_CONTRACT_VERSION


def test_validate_plugin_contract_rejects_missing_entrypoint() -> None:
    exports = _valid_device_exports()
    exports.pop("create_processor")

    with pytest.raises(PluginContractError, match="create_processor"):
        validate_plugin_contract(exports)


def test_validate_plugin_contract_rejects_duplicate_plugin_id() -> None:
    with pytest.raises(DuplicatePluginRegistrationError, match="device.sample"):
        validate_plugin_contract(
            _valid_device_exports(),
            seen_plugin_ids={"device.sample"},
        )


def test_validate_plugin_contract_rejects_invalid_capability_type() -> None:
    exports = _valid_device_exports()
    exports["capabilities"] = lambda: {
        "can_process": "yes",
        "supports_preprocess": False,
        "supports_batch": False,
        "supports_sync": False,
    }

    with pytest.raises(PluginContractError, match="can_process"):
        validate_plugin_contract(exports)


def test_validate_plugin_contract_rejects_invalid_capability_combination() -> None:
    exports = _valid_device_exports()
    exports["capabilities"] = lambda: PluginCapabilities(
        can_process=False,
        supports_preprocess=True,
        supports_batch=False,
        supports_sync=False,
    )

    with pytest.raises(PluginContractError, match="supports_preprocess"):
        validate_plugin_contract(exports)


def test_validate_plugin_contract_rejects_device_without_can_process() -> None:
    exports = _valid_device_exports()
    exports["capabilities"] = lambda: PluginCapabilities(
        can_process=False,
        supports_preprocess=False,
        supports_batch=False,
        supports_sync=False,
    )

    with pytest.raises(PluginContractError, match="device"):
        validate_plugin_contract(exports)


def test_validate_plugin_contract_rejects_pc_without_sync_capability() -> None:
    exports = _valid_pc_exports()
    exports["capabilities"] = lambda: PluginCapabilities(
        can_process=False,
        supports_preprocess=False,
        supports_batch=False,
        supports_sync=False,
    )

    with pytest.raises(PluginContractError, match="supports_sync"):
        validate_plugin_contract(exports)


def test_validate_plugin_contract_rejects_invalid_processor_factory_output() -> None:
    exports = _valid_device_exports()
    exports["create_processor"] = lambda settings: object()

    with pytest.raises(InvalidProcessorError):
        validate_plugin_contract(exports)


def test_processor_descriptor_and_result_validation() -> None:
    descriptor = ProcessorDescriptor(
        plugin_id="device.sample",
        processor_kind="default",
        version="1.2.3",
    )
    assert descriptor.plugin_id == "device.sample"

    result = validate_processor_result(
        {
            "final_path": "D:/processed/file.tif",
            "datatype": "image/tiff",
            "force_paths": ["D:/processed/aux.bin"],
        }
    )
    assert result == ProcessorResult(
        final_path="D:/processed/file.tif",
        datatype="image/tiff",
        force_paths=("D:/processed/aux.bin",),
    )


def test_validate_processor_result_rejects_invalid_shape() -> None:
    with pytest.raises(InvalidProcessorError):
        validate_processor_result({"datatype": "missing-final-path"})


def test_contract_version_compatibility_rules() -> None:
    assert is_contract_version_compatible(PLUGIN_CONTRACT_VERSION) is True
    assert is_contract_version_compatible("2.9.0") is True
    assert is_contract_version_compatible("3.0.0") is False
    assert is_contract_version_compatible("1.9.9") is False
