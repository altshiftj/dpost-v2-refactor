"""Runtime UI factory adapter helpers for dpost composition wiring."""

from __future__ import annotations

from typing import Callable

from dpost.infrastructure.runtime.headless_ui import HeadlessRuntimeUI


def resolve_ui_factory(mode_name: str) -> Callable[[], object]:
    """Return the UI factory that matches the requested runtime mode."""
    if mode_name == "desktop":
        from ipat_watchdog.core.ui.ui_tkinter import TKinterUI

        return TKinterUI
    return HeadlessRuntimeUI
