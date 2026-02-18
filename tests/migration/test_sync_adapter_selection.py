"""Migration tests for Phase 3 sync adapter contract and selection."""

from __future__ import annotations

import importlib
import sys
from types import ModuleType, SimpleNamespace

import pytest

from dpost.infrastructure.sync import NoopSyncAdapter


def _reload_composition_module() -> ModuleType:
    """Reload the dpost composition module with a clean import state."""
    sys.modules.pop("dpost.runtime.composition", None)
    sys.modules.pop("ipat_watchdog.core.sync.sync_kadi", None)
    return importlib.import_module("dpost.runtime.composition")


def test_composition_import_does_not_eagerly_import_kadi() -> None:
    """Ensure framework composition can load without eager Kadi imports."""
    sys.modules.pop("ipat_watchdog.core.app.bootstrap", None)
    sys.modules.pop("ipat_watchdog.core.sync.sync_kadi", None)

    _reload_composition_module()

    assert "ipat_watchdog.core.sync.sync_kadi" not in sys.modules


def test_default_sync_adapter_selection_uses_noop() -> None:
    """Resolve the default sync adapter to the reference noop adapter."""
    composition = _reload_composition_module()

    adapter = composition.select_sync_adapter()

    assert adapter.__class__.__name__ == "NoopSyncAdapter"


def test_unknown_sync_adapter_name_raises_startup_error() -> None:
    """Raise a startup error when a configured adapter name is unknown."""
    from ipat_watchdog.core.app.bootstrap import StartupError

    composition = _reload_composition_module()

    with pytest.raises(StartupError, match="Unknown sync adapter"):
        composition.select_sync_adapter("missing-adapter")


def test_compose_bootstrap_wires_noop_sync_factory(monkeypatch) -> None:
    """Wire noop sync adapter factory into legacy bootstrap composition."""
    composition = _reload_composition_module()
    captured: dict[str, object] = {}
    bootstrap_module = importlib.import_module("ipat_watchdog.core.app.bootstrap")

    def fake_bootstrap(*args, **kwargs):
        captured["kwargs"] = kwargs
        return SimpleNamespace(app=SimpleNamespace(run=lambda: None))

    monkeypatch.setattr(bootstrap_module, "bootstrap", fake_bootstrap)
    monkeypatch.setenv("DPOST_SYNC_ADAPTER", "noop")

    composition.compose_bootstrap()

    assert "sync_manager_factory" in captured["kwargs"]
    adapter_factory = captured["kwargs"]["sync_manager_factory"]
    adapter = adapter_factory(object())
    assert isinstance(adapter, NoopSyncAdapter)


def test_compose_bootstrap_unknown_adapter_from_env_raises_startup_error(
    monkeypatch,
) -> None:
    """Raise startup error when env-selected sync adapter is unknown."""
    from ipat_watchdog.core.app.bootstrap import StartupError

    composition = _reload_composition_module()
    called = {"bootstrap_called": False}
    bootstrap_module = importlib.import_module("ipat_watchdog.core.app.bootstrap")

    def fake_bootstrap(*args, **kwargs):
        called["bootstrap_called"] = True
        return SimpleNamespace(app=SimpleNamespace(run=lambda: None))

    monkeypatch.setattr(bootstrap_module, "bootstrap", fake_bootstrap)
    monkeypatch.setenv("DPOST_SYNC_ADAPTER", "missing-adapter")

    with pytest.raises(StartupError, match="Unknown sync adapter"):
        composition.compose_bootstrap()

    assert called["bootstrap_called"] is False


def test_compose_bootstrap_wires_kadi_sync_factory_from_env(monkeypatch) -> None:
    """Wire Kadi sync adapter factory into startup when selected from env."""
    composition = _reload_composition_module()
    captured: dict[str, object] = {}
    bootstrap_module = importlib.import_module("ipat_watchdog.core.app.bootstrap")
    fake_kadi_module = ModuleType("dpost.infrastructure.sync.kadi")

    class KadiSyncAdapter:
        """Test double for the Kadi sync adapter contract implementation."""

        def sync_record_to_database(self, local_record: object) -> bool:
            return False

    fake_kadi_module.KadiSyncAdapter = KadiSyncAdapter

    def fake_bootstrap(*args, **kwargs):
        captured["kwargs"] = kwargs
        return SimpleNamespace(app=SimpleNamespace(run=lambda: None))

    monkeypatch.setitem(sys.modules, "dpost.infrastructure.sync.kadi", fake_kadi_module)
    monkeypatch.setattr(bootstrap_module, "bootstrap", fake_bootstrap)
    monkeypatch.setenv("DPOST_SYNC_ADAPTER", "kadi")

    composition.compose_bootstrap()

    assert "sync_manager_factory" in captured["kwargs"]
    adapter_factory = captured["kwargs"]["sync_manager_factory"]
    adapter = adapter_factory(object())
    assert isinstance(adapter, KadiSyncAdapter)


def test_kadi_sync_adapter_missing_dependency_raises_startup_error(
    monkeypatch,
) -> None:
    """Raise startup error when the Kadi optional dependency is unavailable."""
    from ipat_watchdog.core.app.bootstrap import StartupError

    composition = _reload_composition_module()
    fake_kadi_module = ModuleType("dpost.infrastructure.sync.kadi")

    class KadiSyncAdapter:
        """Test double that simulates missing optional dependency at init."""

        def __init__(self) -> None:
            raise ModuleNotFoundError("No module named 'kadi_apy'")

        def sync_record_to_database(self, local_record: object) -> bool:
            return False

    fake_kadi_module.KadiSyncAdapter = KadiSyncAdapter

    monkeypatch.setitem(sys.modules, "dpost.infrastructure.sync.kadi", fake_kadi_module)

    with pytest.raises(StartupError, match="kadi_apy"):
        composition.select_sync_adapter("kadi")
