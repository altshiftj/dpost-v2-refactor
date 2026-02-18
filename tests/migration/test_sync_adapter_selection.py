"""Migration tests for Phase 3 sync adapter contract and selection."""

from __future__ import annotations

import importlib
import sys
from types import ModuleType

import pytest


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
