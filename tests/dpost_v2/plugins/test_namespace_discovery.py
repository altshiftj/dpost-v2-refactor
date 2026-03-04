from __future__ import annotations

from types import ModuleType, SimpleNamespace

import pytest

from dpost_v2.application.contracts.plugin_contracts import PLUGIN_CONTRACT_VERSION
from dpost_v2.plugins.discovery import discover_from_namespaces
from dpost_v2.plugins.discovery import PluginDiscoveryFamilyError


def test_namespace_discovery_finds_v2_test_device_and_pc_plugins() -> None:
    discovered = discover_from_namespaces()

    plugin_ids = tuple(descriptor.plugin_id for descriptor in discovered.descriptors)

    assert "test_device" in plugin_ids
    assert "test_pc" in plugin_ids


def test_namespace_discovery_skips_template_packages_by_default() -> None:
    discovered = discover_from_namespaces()

    plugin_ids = tuple(descriptor.plugin_id for descriptor in discovered.descriptors)

    assert "device.template" not in plugin_ids
    assert "pc.template" not in plugin_ids


def test_namespace_discovery_rejects_namespace_family_mismatch() -> None:
    namespace_devices = ModuleType("lane.plugins.devices")
    namespace_devices.__path__ = ["lane-devices"]  # type: ignore[attr-defined]
    namespace_pcs = ModuleType("lane.plugins.pcs")
    namespace_pcs.__path__ = ["lane-pcs"]  # type: ignore[attr-defined]

    mismatch_module = ModuleType("lane.plugins.devices.mismatch.plugin")
    mismatch_module.metadata = lambda: {
        "plugin_id": "pc.mismatch",
        "family": "pc",
        "version": "1.0.0",
        "contract_version": PLUGIN_CONTRACT_VERSION,
        "supported_profiles": ("prod",),
    }
    mismatch_module.capabilities = lambda: {
        "can_process": False,
        "supports_preprocess": False,
        "supports_batch": False,
        "supports_sync": True,
    }
    mismatch_module.create_sync_adapter = lambda _settings: object()
    mismatch_module.prepare_sync_payload = lambda _record, _context: {"record_id": "r1"}

    modules = {
        "lane.plugins.devices": namespace_devices,
        "lane.plugins.pcs": namespace_pcs,
        "lane.plugins.devices.mismatch.plugin": mismatch_module,
    }

    def importer(name: str) -> object:
        if name in modules:
            return modules[name]
        raise ModuleNotFoundError(name)

    def iter_modules(paths, *, prefix: str):
        del paths
        if prefix == "lane.plugins.devices.":
            return [SimpleNamespace(ispkg=True, name="lane.plugins.devices.mismatch")]
        return []

    with pytest.raises(PluginDiscoveryFamilyError, match="pc.mismatch"):
        discover_from_namespaces(
            namespace_families={
                "lane.plugins.devices": "device",
                "lane.plugins.pcs": "pc",
            },
            module_importer=importer,
            iter_modules_fn=iter_modules,
        )
