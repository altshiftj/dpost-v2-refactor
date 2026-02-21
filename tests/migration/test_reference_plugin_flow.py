"""Migration tests for Phase 3 reference plugin flow wiring."""

from __future__ import annotations

import importlib
import sys
from types import ModuleType, SimpleNamespace

import pytest


def _reload_composition_module() -> ModuleType:
    """Reload the dpost composition module with a clean import state."""
    sys.modules.pop("dpost.runtime.composition", None)
    return importlib.import_module("dpost.runtime.composition")


def test_compose_bootstrap_reference_plugin_profile_wires_startup_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Wire reference plugin profile through composition without concrete coupling."""
    composition = _reload_composition_module()
    captured: dict[str, object] = {}
    bootstrap_module = importlib.import_module("dpost.runtime.bootstrap")

    def fake_bootstrap(*args, **kwargs):
        captured["kwargs"] = kwargs
        return SimpleNamespace(app=SimpleNamespace(run=lambda: None))

    monkeypatch.setattr(bootstrap_module, "bootstrap", fake_bootstrap)
    monkeypatch.setenv("DPOST_SYNC_ADAPTER", "noop")
    monkeypatch.setenv("DPOST_PLUGIN_PROFILE", "reference")

    composition.compose_bootstrap()

    assert "settings" in captured["kwargs"]
    settings = captured["kwargs"]["settings"]
    assert settings.pc_name == "test_pc"
    assert settings.device_names == ("test_device",)
