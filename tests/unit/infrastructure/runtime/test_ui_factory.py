"""Unit coverage for runtime UI factory resolution helpers."""

from __future__ import annotations

import dpost.infrastructure.runtime.ui_factory as ui_factory_module
from dpost.infrastructure.runtime.headless_ui import HeadlessRuntimeUI


def test_resolve_ui_factory_returns_desktop_factory_for_desktop_mode() -> None:
    """Return desktop UI factory from desktop factory provider."""
    sentinel_factory = object()
    original = ui_factory_module.get_desktop_ui_class
    ui_factory_module.get_desktop_ui_class = lambda: sentinel_factory
    try:
        resolved = ui_factory_module.resolve_ui_factory("desktop")
    finally:
        ui_factory_module.get_desktop_ui_class = original

    assert resolved is sentinel_factory


def test_resolve_ui_factory_defaults_to_headless_for_other_modes() -> None:
    """Return headless UI implementation for non-desktop runtime modes."""
    resolved = ui_factory_module.resolve_ui_factory("headless")
    assert resolved is HeadlessRuntimeUI
