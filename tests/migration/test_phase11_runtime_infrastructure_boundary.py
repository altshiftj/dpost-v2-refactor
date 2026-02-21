"""Migration tests for Phase 11 runtime infrastructure boundary extraction."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType

from dpost.infrastructure.runtime import HeadlessRuntimeUI
from ipat_watchdog.core.ui.ui_tkinter import TKinterUI

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DPOST_COMPOSITION_PATH = PROJECT_ROOT / "src" / "dpost" / "runtime" / "composition.py"
DPOST_HEADLESS_UI_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "infrastructure" / "runtime" / "headless_ui.py"
)
DPOST_UI_FACTORY_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "infrastructure" / "runtime" / "ui_factory.py"
)
DPOST_BOOTSTRAP_DEPENDENCIES_PATH = (
    PROJECT_ROOT
    / "src"
    / "dpost"
    / "infrastructure"
    / "runtime"
    / "bootstrap_dependencies.py"
)
DPOST_CONFIG_DEPENDENCIES_PATH = (
    PROJECT_ROOT
    / "src"
    / "dpost"
    / "infrastructure"
    / "runtime"
    / "config_dependencies.py"
)
DPOST_SYNC_KADI_ADAPTER_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "infrastructure" / "sync" / "kadi.py"
)
DPOST_SYNC_KADI_MANAGER_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "infrastructure" / "sync" / "kadi_manager.py"
)


def _reload_composition_module() -> ModuleType:
    """Reload dpost composition module with a clean import state."""
    sys.modules.pop("dpost.runtime.composition", None)
    return importlib.import_module("dpost.runtime.composition")


def test_runtime_composition_has_no_direct_legacy_tk_import() -> None:
    """Require runtime composition to avoid direct legacy Tk import coupling."""
    composition_contents = DPOST_COMPOSITION_PATH.read_text(encoding="utf-8")

    assert "ipat_watchdog.core.ui.ui_tkinter" not in composition_contents


def test_headless_runtime_ui_has_no_direct_legacy_ui_contract_imports() -> None:
    """Require headless runtime UI typing contracts to be dpost-owned."""
    headless_ui_contents = DPOST_HEADLESS_UI_PATH.read_text(encoding="utf-8")

    assert "ipat_watchdog.core.interactions" not in headless_ui_contents
    assert "ipat_watchdog.core.ui.ui_abstract" not in headless_ui_contents


def test_bootstrap_dependencies_has_no_direct_legacy_ui_adapter_imports() -> None:
    """Require runtime bootstrap dependencies to use dpost-owned UI adapters."""
    dependency_contents = DPOST_BOOTSTRAP_DEPENDENCIES_PATH.read_text(encoding="utf-8")

    assert "ipat_watchdog.core.ui.adapters" not in dependency_contents


def test_ui_factory_and_bootstrap_dependencies_have_no_direct_legacy_tk_import() -> (
    None
):
    """Require desktop UI loading to flow through dpost infrastructure boundaries."""
    ui_factory_contents = DPOST_UI_FACTORY_PATH.read_text(encoding="utf-8")
    dependency_contents = DPOST_BOOTSTRAP_DEPENDENCIES_PATH.read_text(encoding="utf-8")

    assert "ipat_watchdog.core.ui.ui_tkinter" not in ui_factory_contents
    assert "ipat_watchdog.core.ui.ui_tkinter" not in dependency_contents


def test_bootstrap_dependencies_has_no_direct_legacy_sync_manager_import() -> None:
    """Require sync manager construction to flow through dpost sync adapters."""
    dependency_contents = DPOST_BOOTSTRAP_DEPENDENCIES_PATH.read_text(encoding="utf-8")

    assert "ipat_watchdog.core.sync.sync_kadi" not in dependency_contents


def test_bootstrap_dependencies_avoid_direct_legacy_config_and_storage_imports() -> (
    None
):
    """Require config/storage wiring to flow through dedicated dpost dependency modules."""
    dependency_contents = DPOST_BOOTSTRAP_DEPENDENCIES_PATH.read_text(encoding="utf-8")

    assert "ipat_watchdog.core.config" not in dependency_contents
    assert "ipat_watchdog.core.storage.filesystem_utils" not in dependency_contents


def test_config_dependency_module_avoids_direct_legacy_config_imports() -> None:
    """Require config dependency shim to resolve config service via dpost config boundary."""
    dependency_contents = DPOST_CONFIG_DEPENDENCIES_PATH.read_text(encoding="utf-8")

    assert "ipat_watchdog.core.config" not in dependency_contents


def test_config_dependency_module_avoids_direct_legacy_storage_imports() -> None:
    """Require config dependency shim to resolve storage init via dpost storage boundary."""
    dependency_contents = DPOST_CONFIG_DEPENDENCIES_PATH.read_text(encoding="utf-8")

    assert "ipat_watchdog.core.storage.filesystem_utils" not in dependency_contents


def test_sync_kadi_adapter_avoids_direct_legacy_sync_manager_import() -> None:
    """Require dpost Kadi adapter to resolve manager via dpost-owned sync modules."""
    adapter_contents = DPOST_SYNC_KADI_ADAPTER_PATH.read_text(encoding="utf-8")

    assert "ipat_watchdog.core.sync.sync_kadi" not in adapter_contents


def test_dpost_sync_kadi_manager_module_exists_with_kadi_sync_manager_class() -> None:
    """Require dpost sync manager module to define KadiSyncManager ownership seam."""
    manager_contents = DPOST_SYNC_KADI_MANAGER_PATH.read_text(encoding="utf-8")

    assert "class KadiSyncManager" in manager_contents


def test_select_ui_factory_delegates_to_infrastructure_ui_factory(
    monkeypatch,
) -> None:
    """Require composition UI selection to delegate via infrastructure adapter."""
    composition = _reload_composition_module()
    sentinel_factory = object()
    captured: dict[str, object] = {}

    def fake_resolve_ui_factory(mode_name: str) -> object:
        captured["mode_name"] = mode_name
        return sentinel_factory

    monkeypatch.setattr(composition, "resolve_ui_factory", fake_resolve_ui_factory)

    resolved_factory = composition.select_ui_factory("desktop")

    assert resolved_factory is sentinel_factory
    assert captured["mode_name"] == "desktop"


def test_infrastructure_ui_factory_resolves_headless_and_desktop_modes() -> None:
    """Require runtime infrastructure adapter to resolve both supported UI modes."""
    from dpost.infrastructure.runtime.ui_factory import resolve_ui_factory

    assert resolve_ui_factory("headless") is HeadlessRuntimeUI
    assert resolve_ui_factory("desktop") is TKinterUI
