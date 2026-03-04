from __future__ import annotations

from types import MappingProxyType

import pytest

from dpost_v2.application.contracts.plugin_contracts import (
    PLUGIN_CONTRACT_VERSION,
    PluginCapabilities,
)
from dpost_v2.plugins.catalog import (
    PluginCatalogDuplicateError,
    build_catalog,
    query_by_capability,
    query_by_family,
    refresh_catalog,
)
from dpost_v2.plugins.discovery import PluginDescriptor


def _descriptor(
    *,
    plugin_id: str,
    family: str,
    profiles: tuple[str, ...] = ("prod",),
    can_process: bool = False,
    supports_sync: bool = False,
) -> PluginDescriptor:
    return PluginDescriptor(
        plugin_id=plugin_id,
        family=family,
        version="1.0.0",
        contract_version=PLUGIN_CONTRACT_VERSION,
        supported_profiles=profiles,
        capabilities=PluginCapabilities(
            can_process=can_process,
            supports_preprocess=False,
            supports_batch=False,
            supports_sync=supports_sync,
        ),
        module_name=f"tests.plugins.{plugin_id}",
        module_exports=MappingProxyType({}),
    )


def test_catalog_builds_deterministic_indexes_and_queries() -> None:
    catalog = build_catalog(
        (
            _descriptor(
                plugin_id="pc.gamma",
                family="pc",
                can_process=False,
                supports_sync=True,
            ),
            _descriptor(
                plugin_id="device.alpha",
                family="device",
                can_process=True,
                supports_sync=False,
            ),
            _descriptor(
                plugin_id="device.beta",
                family="device",
                profiles=(),
                can_process=True,
                supports_sync=False,
            ),
        )
    )

    assert tuple(item.plugin_id for item in catalog.descriptors) == (
        "device.alpha",
        "device.beta",
        "pc.gamma",
    )
    assert tuple(item.plugin_id for item in query_by_family(catalog, "device")) == (
        "device.alpha",
        "device.beta",
    )
    assert tuple(
        item.plugin_id for item in query_by_capability(catalog, "supports_sync")
    ) == ("pc.gamma",)
    assert tuple(item.plugin_id for item in catalog.by_profile["prod"]) == (
        "device.alpha",
        "device.beta",
        "pc.gamma",
    )


def test_catalog_rejects_duplicate_plugin_ids() -> None:
    duplicate = _descriptor(
        plugin_id="device.shared",
        family="device",
        can_process=True,
    )

    with pytest.raises(PluginCatalogDuplicateError, match="device.shared"):
        build_catalog((duplicate, duplicate))


def test_catalog_refresh_returns_diff_and_new_version() -> None:
    initial = build_catalog(
        (
            _descriptor(plugin_id="device.alpha", family="device", can_process=True),
            _descriptor(plugin_id="pc.gamma", family="pc", supports_sync=True),
        )
    )
    refreshed, diff = refresh_catalog(
        initial,
        (
            _descriptor(plugin_id="device.alpha", family="device", can_process=True),
            _descriptor(plugin_id="device.beta", family="device", can_process=True),
        ),
        expected_version=initial.version,
    )

    assert diff.added_plugin_ids == ("device.beta",)
    assert diff.removed_plugin_ids == ("pc.gamma",)
    assert refreshed.version != initial.version


def test_catalog_snapshot_mappings_are_immutable() -> None:
    catalog = build_catalog(
        (_descriptor(plugin_id="device.alpha", family="device", can_process=True),)
    )

    with pytest.raises(TypeError):
        catalog.by_id["x"] = catalog.by_id["device.alpha"]  # type: ignore[index]
