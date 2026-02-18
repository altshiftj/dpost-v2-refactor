"""Migration tests for Phase 4 configuration consolidation behavior."""

from __future__ import annotations

import importlib
import sys
from types import ModuleType, SimpleNamespace

import pytest


def _reload_composition_module() -> ModuleType:
    """Reload the dpost composition module with a clean import state."""
    sys.modules.pop("dpost.runtime.composition", None)
    return importlib.import_module("dpost.runtime.composition")


@pytest.fixture(autouse=True)
def _clear_dpost_startup_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear Phase 4 startup env vars before each test."""
    for key in (
        "DPOST_PC_NAME",
        "DPOST_DEVICE_PLUGINS",
        "DPOST_PROMETHEUS_PORT",
        "DPOST_OBSERVABILITY_PORT",
    ):
        monkeypatch.delenv(key, raising=False)


def test_resolve_startup_settings_defaults_to_none() -> None:
    """Resolve no explicit startup settings when no overrides are provided."""
    composition = _reload_composition_module()

    settings = composition.resolve_startup_settings()

    assert settings is None


def test_resolve_startup_settings_prefers_explicit_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Use explicit startup overrides instead of conflicting environment values."""
    composition = _reload_composition_module()
    monkeypatch.setenv("DPOST_PC_NAME", "env_pc")
    monkeypatch.setenv("DPOST_DEVICE_PLUGINS", "env_one,env_two")
    monkeypatch.setenv("DPOST_PROMETHEUS_PORT", "9300")
    monkeypatch.setenv("DPOST_OBSERVABILITY_PORT", "9301")

    settings = composition.resolve_startup_settings(
        pc_name="explicit_pc",
        device_names=("explicit_one", "explicit_two"),
        prometheus_port=9400,
        observability_port=9401,
    )

    assert settings is not None
    assert settings.pc_name == "explicit_pc"
    assert settings.device_names == ("explicit_one", "explicit_two")
    assert settings.prometheus_port == 9400
    assert settings.observability_port == 9401


def test_compose_bootstrap_reads_env_driven_startup_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pass env-driven startup settings through composition into legacy bootstrap."""
    composition = _reload_composition_module()
    captured: dict[str, object] = {}
    bootstrap_module = importlib.import_module("ipat_watchdog.core.app.bootstrap")

    def fake_bootstrap(*args, **kwargs):
        captured["kwargs"] = kwargs
        return SimpleNamespace(app=SimpleNamespace(run=lambda: None))

    monkeypatch.setattr(bootstrap_module, "bootstrap", fake_bootstrap)
    monkeypatch.setenv("DPOST_SYNC_ADAPTER", "noop")
    monkeypatch.delenv("DPOST_PLUGIN_PROFILE", raising=False)
    monkeypatch.setenv("DPOST_PC_NAME", "env_pc")
    monkeypatch.setenv("DPOST_DEVICE_PLUGINS", "env_one; env_two")
    monkeypatch.setenv("DPOST_PROMETHEUS_PORT", "9300")
    monkeypatch.setenv("DPOST_OBSERVABILITY_PORT", "9301")

    composition.compose_bootstrap()

    assert "settings" in captured["kwargs"]
    settings = captured["kwargs"]["settings"]
    assert settings.pc_name == "env_pc"
    assert settings.device_names == ("env_one", "env_two")
    assert settings.prometheus_port == 9300
    assert settings.observability_port == 9301


def _raise_missing_config_service() -> None:
    """Raise the canonical runtime error for missing config service."""
    raise RuntimeError("Configuration service has not been initialised")


def test_init_dirs_without_explicit_directories_requires_active_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject implicit directory initialisation when config service is unavailable."""
    filesystem_utils = importlib.import_module(
        "ipat_watchdog.core.storage.filesystem_utils"
    )
    monkeypatch.setattr(filesystem_utils, "current", _raise_missing_config_service)

    with pytest.raises(
        RuntimeError, match="Configuration service has not been initialised"
    ):
        filesystem_utils.init_dirs()


def test_get_record_path_requires_active_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject implicit destination path resolution when config service is unavailable."""
    filesystem_utils = importlib.import_module(
        "ipat_watchdog.core.storage.filesystem_utils"
    )
    monkeypatch.setattr(filesystem_utils, "current", _raise_missing_config_service)

    with pytest.raises(
        RuntimeError, match="Configuration service has not been initialised"
    ):
        filesystem_utils.get_record_path("usr-ipat-sample", device_abbr="UTM")
