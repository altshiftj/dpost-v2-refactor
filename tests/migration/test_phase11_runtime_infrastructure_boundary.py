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


def _reload_composition_module() -> ModuleType:
    """Reload dpost composition module with a clean import state."""
    sys.modules.pop("dpost.runtime.composition", None)
    return importlib.import_module("dpost.runtime.composition")


def test_runtime_composition_has_no_direct_legacy_tk_import() -> None:
    """Require runtime composition to avoid direct legacy Tk import coupling."""
    composition_contents = DPOST_COMPOSITION_PATH.read_text(encoding="utf-8")

    assert "ipat_watchdog.core.ui.ui_tkinter" not in composition_contents


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
