"""Migration tests for dpost plugin-loading ownership boundaries."""

from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DPOST_RUNTIME_BOOTSTRAP_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "runtime" / "bootstrap.py"
)
DPOST_PLUGIN_LOADING_PATH = PROJECT_ROOT / "src" / "dpost" / "plugins" / "loading.py"
DPOST_PLUGIN_SYSTEM_PATH = PROJECT_ROOT / "src" / "dpost" / "plugins" / "system.py"


def test_runtime_bootstrap_has_no_direct_legacy_loader_dependency() -> None:
    """Require runtime bootstrap to resolve plugins via dpost plugin boundaries."""
    bootstrap_contents = DPOST_RUNTIME_BOOTSTRAP_PATH.read_text(encoding="utf-8")

    assert "ipat_watchdog.loader" not in bootstrap_contents


def test_plugin_loading_boundaries_use_dpost_owned_plugin_contract_types() -> None:
    """Require dpost plugin loading/modules to avoid legacy plugin base imports."""
    loading_contents = DPOST_PLUGIN_LOADING_PATH.read_text(encoding="utf-8")
    system_contents = DPOST_PLUGIN_SYSTEM_PATH.read_text(encoding="utf-8")

    assert "ipat_watchdog.device_plugins.device_plugin" not in loading_contents
    assert "ipat_watchdog.pc_plugins.pc_plugin" not in loading_contents
    assert "ipat_watchdog.device_plugins.device_plugin" not in system_contents
    assert "ipat_watchdog.pc_plugins.pc_plugin" not in system_contents


def test_plugin_system_uses_dpost_owned_plugin_namespace_groups() -> None:
    """Require plugin discovery/runtime groups to be dpost-owned by default."""
    system_contents = DPOST_PLUGIN_SYSTEM_PATH.read_text(encoding="utf-8")

    assert 'DEVICE_ENTRYPOINT_GROUP = "dpost.device_plugins"' in system_contents
    assert 'PC_ENTRYPOINT_GROUP = "dpost.pc_plugins"' in system_contents


def test_dpost_plugin_loading_resolves_reference_pc_devices() -> None:
    """Require dpost plugin-loading boundary to resolve reference PC devices."""
    from dpost.plugins.loading import get_devices_for_pc

    assert get_devices_for_pc("test_pc") == ["test_device"]


def test_dpost_plugin_loader_unknown_plugin_message_is_actionable() -> None:
    """Require dpost plugin-loading boundary errors to remain actionable."""
    from dpost.plugins.loading import load_device_plugin

    with pytest.raises(RuntimeError) as exc_info:
        load_device_plugin("missing-device")

    error_message = str(exc_info.value)
    assert "missing-device" in error_message
    assert "available device plugins" in error_message.lower()
    assert "test_device" in error_message
