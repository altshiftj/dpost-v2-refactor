from __future__ import annotations

from dpost_v2.plugins.discovery import discover_from_namespaces


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
