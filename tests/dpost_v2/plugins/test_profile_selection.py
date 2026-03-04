from __future__ import annotations

from types import MappingProxyType

import pytest

from dpost_v2.application.contracts.plugin_contracts import (
    PLUGIN_CONTRACT_VERSION,
    PluginCapabilities,
)
from dpost_v2.plugins.catalog import build_catalog
from dpost_v2.plugins.discovery import PluginDescriptor
from dpost_v2.plugins.profile_selection import (
    PluginProfileCatalogMismatchError,
    PluginProfileOverrideConflictError,
    PluginProfileUnknownError,
    select_plugins_for_profile,
)


def _descriptor(
    *,
    plugin_id: str,
    family: str,
    profiles: tuple[str, ...],
    can_process: bool,
    supports_sync: bool,
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


def _catalog():
    return build_catalog(
        (
            _descriptor(
                plugin_id="device.alpha",
                family="device",
                profiles=("prod", "qa"),
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
            _descriptor(
                plugin_id="pc.gamma",
                family="pc",
                profiles=("prod",),
                can_process=False,
                supports_sync=True,
            ),
        )
    )


def test_profile_selection_is_deterministic_for_identical_inputs() -> None:
    catalog = _catalog()

    first = select_plugins_for_profile(
        catalog,
        profile="prod",
        known_profiles={"prod", "qa"},
    )
    second = select_plugins_for_profile(
        catalog,
        profile="prod",
        known_profiles={"qa", "prod"},
    )

    assert first.selected_by_family == {
        "device": ("device.alpha", "device.beta"),
        "pc": ("pc.gamma",),
    }
    assert first.selected_by_family == second.selected_by_family
    assert first.fingerprint == second.fingerprint


def test_profile_selection_applies_deny_before_allow_overrides() -> None:
    catalog = _catalog()

    selected = select_plugins_for_profile(
        catalog,
        profile="prod",
        known_profiles={"prod", "qa"},
        allow_plugin_ids={"device.alpha"},
        deny_plugin_ids={"pc.gamma"},
    )

    assert selected.selected_by_family == {
        "device": ("device.alpha", "device.beta"),
        "pc": (),
    }
    assert selected.diagnostics["excluded"]["pc.gamma"] == "deny_override"
    assert selected.diagnostics["included"]["device.alpha"] == "allow_override"


def test_profile_selection_rejects_unknown_profile_token() -> None:
    with pytest.raises(PluginProfileUnknownError, match="staging"):
        select_plugins_for_profile(
            _catalog(),
            profile="staging",
            known_profiles={"prod", "qa"},
        )


def test_profile_selection_rejects_conflicting_allow_deny_overrides() -> None:
    with pytest.raises(PluginProfileOverrideConflictError, match="device.alpha"):
        select_plugins_for_profile(
            _catalog(),
            profile="prod",
            known_profiles={"prod", "qa"},
            allow_plugin_ids={"device.alpha"},
            deny_plugin_ids={"device.alpha"},
        )


def test_profile_selection_rejects_overrides_for_missing_catalog_plugin() -> None:
    with pytest.raises(PluginProfileCatalogMismatchError, match="device.missing"):
        select_plugins_for_profile(
            _catalog(),
            profile="prod",
            known_profiles={"prod", "qa"},
            allow_plugin_ids={"device.missing"},
        )
