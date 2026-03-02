"""Runtime UI factory adapter helpers for dpost composition wiring."""

from __future__ import annotations

from typing import Callable

from dpost.infrastructure.runtime_adapters.desktop_ui import get_desktop_ui_class
from dpost.infrastructure.runtime_adapters.headless_ui import HeadlessRuntimeUI


def resolve_ui_factory(mode_name: str) -> Callable[[], object]:
    """Return the UI factory that matches the requested runtime mode."""
    if mode_name == "desktop":
        return get_desktop_ui_class()
    return HeadlessRuntimeUI
