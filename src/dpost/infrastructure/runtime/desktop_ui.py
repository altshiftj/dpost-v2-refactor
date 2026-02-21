"""Desktop runtime UI class resolution boundary for dpost infrastructure."""

from __future__ import annotations


def get_desktop_ui_class():
    """Return the desktop UI class via lazy import of the current backend."""
    from ipat_watchdog.core.ui.ui_tkinter import TKinterUI

    return TKinterUI
