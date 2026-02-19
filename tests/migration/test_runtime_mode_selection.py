"""Migration tests for Phase 7 runtime mode selection and smoke behavior."""

from __future__ import annotations

import importlib
import sys
from types import ModuleType, SimpleNamespace

import pytest

from dpost import __main__ as main_module
from ipat_watchdog.core.ui.ui_tkinter import TKinterUI


def _reload_composition_module() -> ModuleType:
    """Reload the dpost composition module with a clean import state."""
    sys.modules.pop("dpost.runtime.composition", None)
    return importlib.import_module("dpost.runtime.composition")


@pytest.fixture(autouse=True)
def _clear_runtime_mode_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear runtime-mode related environment variables before each test."""
    for key in (
        "DPOST_RUNTIME_MODE",
        "DPOST_SYNC_ADAPTER",
        "DPOST_PLUGIN_PROFILE",
        "DPOST_PC_NAME",
        "DPOST_DEVICE_PLUGINS",
        "DPOST_PROMETHEUS_PORT",
        "DPOST_OBSERVABILITY_PORT",
    ):
        monkeypatch.delenv(key, raising=False)


def _install_bootstrap_stub(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[dict[str, object], dict[str, bool]]:
    """Patch legacy bootstrap and capture bootstrap kwargs plus app run calls."""
    captured: dict[str, object] = {}
    calls = {"run_called": False}
    bootstrap_module = importlib.import_module("ipat_watchdog.core.app.bootstrap")

    class AppStub:
        """App stub that marks whether the runtime loop was invoked."""

        def run(self) -> None:
            """Record execution of the application run path."""
            calls["run_called"] = True

    def fake_bootstrap(*args, **kwargs):
        captured["kwargs"] = kwargs
        return SimpleNamespace(app=AppStub())

    monkeypatch.setattr(bootstrap_module, "bootstrap", fake_bootstrap)
    return captured, calls


def test_default_runtime_mode_selection_is_headless() -> None:
    """Default runtime mode resolves to headless when no override is provided."""
    composition = _reload_composition_module()

    assert composition.select_runtime_mode() == "headless"


def test_unknown_runtime_mode_name_raises_startup_error() -> None:
    """Reject unknown runtime mode names with an actionable startup error."""
    from ipat_watchdog.core.app.bootstrap import StartupError

    composition = _reload_composition_module()

    with pytest.raises(StartupError, match="Unknown runtime mode"):
        composition.select_runtime_mode("invalid-mode")


def test_compose_bootstrap_headless_mode_wires_explicit_non_tk_ui_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Require explicit non-Tk UI factory wiring for headless runtime mode."""
    composition = _reload_composition_module()
    captured, _ = _install_bootstrap_stub(monkeypatch)
    monkeypatch.setenv("DPOST_SYNC_ADAPTER", "noop")
    monkeypatch.setenv("DPOST_RUNTIME_MODE", "headless")

    composition.compose_bootstrap()

    kwargs = captured["kwargs"]
    assert "ui_factory" in kwargs
    assert kwargs["ui_factory"] is not TKinterUI


def test_compose_bootstrap_desktop_mode_wires_explicit_tk_ui_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Require explicit Tk UI factory wiring for desktop runtime mode."""
    composition = _reload_composition_module()
    captured, _ = _install_bootstrap_stub(monkeypatch)
    monkeypatch.setenv("DPOST_SYNC_ADAPTER", "noop")
    monkeypatch.setenv("DPOST_RUNTIME_MODE", "desktop")

    composition.compose_bootstrap()

    kwargs = captured["kwargs"]
    assert "ui_factory" in kwargs
    assert kwargs["ui_factory"] is TKinterUI


def test_main_smoke_headless_runtime_mode_uses_mode_specific_composition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Require headless-mode startup smoke to run through explicit mode wiring."""
    composition = _reload_composition_module()
    captured, calls = _install_bootstrap_stub(monkeypatch)
    monkeypatch.setattr(main_module, "compose_bootstrap", composition.compose_bootstrap)
    monkeypatch.setenv("DPOST_SYNC_ADAPTER", "noop")
    monkeypatch.setenv("DPOST_RUNTIME_MODE", "headless")

    assert main_module.main() == 0
    assert calls["run_called"] is True
    kwargs = captured["kwargs"]
    assert "ui_factory" in kwargs
    assert kwargs["ui_factory"] is not TKinterUI


def test_main_smoke_desktop_runtime_mode_uses_mode_specific_composition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Require desktop-mode startup smoke to run through explicit mode wiring."""
    composition = _reload_composition_module()
    captured, calls = _install_bootstrap_stub(monkeypatch)
    monkeypatch.setattr(main_module, "compose_bootstrap", composition.compose_bootstrap)
    monkeypatch.setenv("DPOST_SYNC_ADAPTER", "noop")
    monkeypatch.setenv("DPOST_RUNTIME_MODE", "desktop")

    assert main_module.main() == 0
    assert calls["run_called"] is True
    kwargs = captured["kwargs"]
    assert "ui_factory" in kwargs
    assert kwargs["ui_factory"] is TKinterUI
