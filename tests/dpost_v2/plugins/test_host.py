from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any

import pytest

from dpost_v2.application.contracts.context import ProcessingContext, RuntimeContext
from dpost_v2.application.contracts.plugin_contracts import (
    PLUGIN_CONTRACT_VERSION,
    PluginCapabilities,
    ProcessorResult,
)
from dpost_v2.plugins.discovery import PluginDescriptor
from dpost_v2.plugins.host import (
    PluginHost,
    PluginHostContractError,
    PluginHostDuplicateIdError,
)


@dataclass
class _Processor:
    plugin_id: str

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
            datatype=f"{self.plugin_id}/output",
        )


def _runtime_context() -> RuntimeContext:
    return RuntimeContext.from_settings(
        settings={
            "mode": "headless",
            "profile": "prod",
            "session_id": "session-host",
            "event_id": "event-host",
            "trace_id": "trace-host",
        },
        dependency_ids={"clock": "clock-1", "ui": "ui-1", "sync": "sync-1"},
    )


def _processing_context() -> ProcessingContext:
    return ProcessingContext.for_candidate(
        runtime_context=_runtime_context(),
        candidate_event={
            "source_path": "D:/incoming/sample.dat",
            "event_type": "created",
            "observed_at": datetime(2026, 3, 4, 10, 5, tzinfo=UTC),
        },
    )


def _device_descriptor(
    *,
    plugin_id: str,
    profiles: tuple[str, ...] = ("prod",),
    hooks: list[tuple[str, str]] | None = None,
) -> PluginDescriptor:
    hook_sink = hooks if hooks is not None else []

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
        return _Processor(plugin_id=plugin_id)

    def validate_settings(raw_settings: dict[str, Any]) -> dict[str, Any]:
        return dict(raw_settings)

    def on_activate(_context: dict[str, Any]) -> None:
        hook_sink.append(("activate", plugin_id))

    def on_shutdown() -> None:
        hook_sink.append(("shutdown", plugin_id))

    return PluginDescriptor(
        plugin_id=plugin_id,
        family="device",
        version="1.0.0",
        contract_version=PLUGIN_CONTRACT_VERSION,
        supported_profiles=profiles,
        capabilities=PluginCapabilities(
            can_process=True,
            supports_preprocess=False,
            supports_batch=False,
            supports_sync=False,
        ),
        module_name=f"tests.plugins.{plugin_id}",
        module_exports=MappingProxyType(
            {
                "metadata": metadata,
                "capabilities": capabilities,
                "create_processor": create_processor,
                "validate_settings": validate_settings,
                "on_activate": on_activate,
                "on_shutdown": on_shutdown,
            }
        ),
    )


def _pc_descriptor(
    *,
    plugin_id: str,
    profiles: tuple[str, ...] = ("prod",),
) -> PluginDescriptor:
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

    return PluginDescriptor(
        plugin_id=plugin_id,
        family="pc",
        version="2.0.0",
        contract_version=PLUGIN_CONTRACT_VERSION,
        supported_profiles=profiles,
        capabilities=PluginCapabilities(
            can_process=False,
            supports_preprocess=False,
            supports_batch=False,
            supports_sync=True,
        ),
        module_name=f"tests.plugins.{plugin_id}",
        module_exports=MappingProxyType(
            {
                "metadata": metadata,
                "capabilities": capabilities,
                "create_sync_adapter": create_sync_adapter,
                "prepare_sync_payload": prepare_sync_payload,
            }
        ),
    )


def test_host_rejects_duplicate_plugin_ids_across_registrations() -> None:
    host = PluginHost()
    descriptor = _device_descriptor(plugin_id="device.alpha")
    host.register_descriptors((descriptor,))

    with pytest.raises(PluginHostDuplicateIdError, match="device.alpha"):
        host.register_descriptors((descriptor,))


def test_host_revalidates_contract_before_registration() -> None:
    descriptor = PluginDescriptor(
        plugin_id="device.invalid",
        family="device",
        version="1.0.0",
        contract_version=PLUGIN_CONTRACT_VERSION,
        supported_profiles=("prod",),
        capabilities=PluginCapabilities(
            can_process=True,
            supports_preprocess=False,
            supports_batch=False,
            supports_sync=False,
        ),
        module_name="tests.plugins.device.invalid",
        module_exports=MappingProxyType(
            {
                "metadata": lambda: {
                    "plugin_id": "device.invalid",
                    "family": "device",
                    "version": "1.0.0",
                    "contract_version": PLUGIN_CONTRACT_VERSION,
                    "supported_profiles": ("prod",),
                },
                "capabilities": lambda: {
                    "can_process": True,
                    "supports_preprocess": False,
                    "supports_batch": False,
                    "supports_sync": False,
                },
            }
        ),
    )

    with pytest.raises(PluginHostContractError, match="create_processor"):
        PluginHost().register_descriptors((descriptor,))


def test_host_capability_lookup_is_deterministic_after_profile_activation() -> None:
    host = PluginHost()
    host.register_descriptors(
        (
            _pc_descriptor(plugin_id="pc.gamma"),
            _device_descriptor(plugin_id="device.beta"),
            _device_descriptor(plugin_id="device.alpha"),
        )
    )

    host.activate_profile(profile="prod", known_profiles={"prod"})

    assert host.get_device_plugins() == ("device.alpha", "device.beta")
    assert host.get_pc_plugins() == ("pc.gamma",)
    assert host.get_by_capability("can_process") == ("device.alpha", "device.beta")
    assert host.get_by_capability("can_process") == ("device.alpha", "device.beta")


def test_host_lifecycle_activation_processor_creation_and_shutdown() -> None:
    hooks: list[tuple[str, str]] = []
    host = PluginHost()
    host.register_descriptors(
        (
            _device_descriptor(plugin_id="device.alpha", hooks=hooks),
            _pc_descriptor(plugin_id="pc.gamma"),
        )
    )

    selection = host.activate_profile(
        profile="prod",
        known_profiles={"prod"},
        deny_plugin_ids={"pc.gamma"},
    )
    processor = host.create_device_processor("device.alpha", settings={"mode": "strict"})
    outcome = processor.process(
        {"source_path": "D:/incoming/alpha.dat"},
        _processing_context(),
    )

    assert selection.selected_by_family == {"device": ("device.alpha",), "pc": ()}
    assert outcome.datatype == "device.alpha/output"
    assert hooks == [("activate", "device.alpha")]

    host.shutdown()

    assert host.get_device_plugins() == ()
    assert hooks == [("activate", "device.alpha"), ("shutdown", "device.alpha")]
