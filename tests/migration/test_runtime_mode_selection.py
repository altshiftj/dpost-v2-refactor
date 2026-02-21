"""Migration tests for Phase 7 runtime mode selection and smoke behavior."""

from __future__ import annotations

import importlib
import sys
from types import ModuleType, SimpleNamespace

import pytest

from dpost import __main__ as main_module
from dpost.application.ports import RenamePrompt, SessionPromptDetails
from dpost.infrastructure.runtime.tkinter_ui import TKinterRuntimeUI


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
    """Patch runtime bootstrap and capture bootstrap kwargs plus app run calls."""
    captured: dict[str, object] = {}
    calls = {"run_called": False}
    bootstrap_module = importlib.import_module("dpost.runtime.bootstrap")

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


def _install_bootstrap_runtime_stubs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch runtime bootstrap dependencies for deterministic composition tests."""
    bootstrap_module = importlib.import_module("dpost.runtime.bootstrap")

    monkeypatch.setattr(bootstrap_module, "_build_config_service", lambda *_: "config")
    monkeypatch.setattr(bootstrap_module, "init_dirs", lambda: None)
    monkeypatch.setattr(bootstrap_module, "start_http_server", lambda *_: None)
    monkeypatch.setattr(
        bootstrap_module, "start_observability_server", lambda *_, **__: None
    )

    class AppStub:
        """App stub that captures interactions and scheduler wiring."""

        def __init__(self, **kwargs) -> None:
            self.interactions = kwargs["interactions"]
            self.scheduler = kwargs["scheduler"]

        def run(self) -> None:
            """No-op run path for composition tests."""

    monkeypatch.setattr(bootstrap_module, "DeviceWatchdogApp", AppStub)


class DesktopUIProbe:
    """UI probe that captures desktop interaction and scheduler calls."""

    def __init__(self) -> None:
        self.append_prompts: list[str] = []
        self.rename_calls: list[tuple[str, dict[str, object]]] = []
        self.done_calls: list[SessionPromptDetails] = []
        self.scheduled_calls: list[tuple[int, object]] = []
        self.cancelled_handles: list[int] = []
        self.handle_counter = 0

    def initialize(self) -> None:
        """Initialize probe UI."""

    def show_warning(self, title: str, message: str) -> None:
        """Record warning calls."""

    def show_info(self, title: str, message: str) -> None:
        """Record info calls."""

    def show_error(self, title: str, message: str) -> None:
        """Record error calls."""

    def prompt_rename(self) -> dict[str, str] | None:
        """Unused legacy probe entrypoint."""
        return None

    def show_rename_dialog(
        self, attempted_filename: str, violation_info: dict[str, object]
    ) -> dict[str, str] | None:
        """Record rename-dialog calls and return deterministic user input."""
        self.rename_calls.append((attempted_filename, violation_info))
        return {"name": "alice", "institute": "lab", "sample_ID": "sample-1"}

    def prompt_append_record(self, record_name: str) -> bool:
        """Record append prompts and return deterministic desktop choice."""
        self.append_prompts.append(record_name)
        return False

    def show_done_dialog(
        self, session_details: SessionPromptDetails, on_done_callback
    ) -> None:
        """Record done prompts and execute callback."""
        self.done_calls.append(session_details)
        on_done_callback()

    def get_root(self) -> object:
        """Return a sentinel root object."""
        return object()

    def destroy(self) -> None:
        """No-op destroy path for probe UI."""

    def schedule_task(self, interval_ms: int, callback) -> int:
        """Record scheduled callbacks and return synthetic handles."""
        self.handle_counter += 1
        self.scheduled_calls.append((interval_ms, callback))
        return self.handle_counter

    def cancel_task(self, handle: int) -> None:
        """Record cancelled scheduled handles."""
        self.cancelled_handles.append(handle)

    def set_close_handler(self, callback) -> None:
        """No-op close handler registration."""

    def set_exception_handler(self, callback) -> None:
        """No-op exception handler registration."""

    def run_main_loop(self) -> None:
        """No-op main loop for probe UI."""


def test_default_runtime_mode_selection_is_headless() -> None:
    """Default runtime mode resolves to headless when no override is provided."""
    composition = _reload_composition_module()

    assert composition.select_runtime_mode() == "headless"


def test_unknown_runtime_mode_name_raises_startup_error() -> None:
    """Reject unknown runtime mode names with an actionable startup error."""
    from dpost.runtime.bootstrap import StartupError

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
    assert kwargs["ui_factory"] is not TKinterRuntimeUI


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
    assert kwargs["ui_factory"] is TKinterRuntimeUI


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
    assert kwargs["ui_factory"] is not TKinterRuntimeUI


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
    assert kwargs["ui_factory"] is TKinterRuntimeUI


def test_desktop_mode_bootstrap_preserves_interaction_and_scheduler_wiring(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Preserve desktop-mode adapter wiring between bootstrap context and app."""
    composition = _reload_composition_module()
    _install_bootstrap_runtime_stubs(monkeypatch)

    tkinter_module = importlib.import_module("dpost.infrastructure.runtime.tkinter_ui")
    monkeypatch.setattr(tkinter_module, "TKinterRuntimeUI", DesktopUIProbe)
    monkeypatch.setenv("DPOST_RUNTIME_MODE", "desktop")
    monkeypatch.setenv("DPOST_SYNC_ADAPTER", "noop")
    monkeypatch.setenv("DPOST_PLUGIN_PROFILE", "reference")

    context = composition.compose_bootstrap()

    assert isinstance(context.ui, DesktopUIProbe)
    assert context.app.interactions is context.interactions
    assert context.app.scheduler is context.scheduler


def test_desktop_mode_preserves_interaction_adapter_behavior(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Preserve desktop-mode interaction and scheduler behavior via adapters."""
    composition = _reload_composition_module()
    _install_bootstrap_runtime_stubs(monkeypatch)

    tkinter_module = importlib.import_module("dpost.infrastructure.runtime.tkinter_ui")
    monkeypatch.setattr(tkinter_module, "TKinterRuntimeUI", DesktopUIProbe)
    monkeypatch.setenv("DPOST_RUNTIME_MODE", "desktop")
    monkeypatch.setenv("DPOST_SYNC_ADAPTER", "noop")
    monkeypatch.setenv("DPOST_PLUGIN_PROFILE", "reference")

    context = composition.compose_bootstrap()
    ui_probe = context.ui

    assert context.interactions.prompt_append_record("record-1") is False
    rename_decision = context.interactions.request_rename(
        RenamePrompt(
            attempted_prefix="bad-prefix",
            analysis={"reasons": ["legacy-reason"]},
            contextual_reason="contextual-reason",
        )
    )
    assert rename_decision.cancelled is False
    assert rename_decision.values == {
        "name": "alice",
        "institute": "lab",
        "sample_ID": "sample-1",
    }
    assert ui_probe.rename_calls
    _attempted_filename, analysis_payload = ui_probe.rename_calls[0]
    assert analysis_payload["reasons"][0] == "contextual-reason"

    done_called = {"value": False}
    context.interactions.show_done_prompt(
        SessionPromptDetails(users=("alice",), records=("record-1",)),
        lambda: done_called.__setitem__("value", True),
    )
    assert done_called["value"] is True

    scheduled_handle = context.scheduler.schedule(25, lambda: None)
    context.scheduler.cancel(scheduled_handle)
    assert scheduled_handle == 1
    assert ui_probe.cancelled_handles == [1]
