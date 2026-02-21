"""Unit coverage for runtime composition-root helper functions."""

from __future__ import annotations

import builtins
from dataclasses import dataclass

import pytest

import dpost.runtime.composition as composition
from dpost.infrastructure.sync import NoopSyncAdapter
from dpost.plugins.reference import REFERENCE_PLUGIN_PROFILE


@dataclass(frozen=True)
class _SentinelSettings:
    """Simple settings payload used by composition tests."""

    value: str


def test_resolve_startup_settings_delegates_to_runtime_boundary() -> None:
    """Pass explicit overrides through to runtime startup-settings resolver."""
    captured_kwargs: dict[str, object] = {}
    expected = _SentinelSettings("resolved")

    def _fake_resolver(**kwargs: object) -> _SentinelSettings:
        captured_kwargs.update(kwargs)
        return expected

    original = composition.resolve_runtime_startup_settings
    composition.resolve_runtime_startup_settings = _fake_resolver
    try:
        resolved = composition.resolve_startup_settings(
            pc_name="pc-x",
            device_names=("dev-a",),
            prometheus_port=9000,
            observability_port=9001,
        )
    finally:
        composition.resolve_runtime_startup_settings = original

    assert resolved == expected
    assert captured_kwargs["pc_name"] == "pc-x"
    assert captured_kwargs["device_names"] == ("dev-a",)
    assert captured_kwargs["prometheus_port"] == 9000
    assert captured_kwargs["observability_port"] == 9001
    assert callable(captured_kwargs["collect_settings"])
    assert callable(captured_kwargs["startup_settings_builder"])
    assert callable(captured_kwargs["startup_error_factory"])


def test_select_sync_adapter_defaults_to_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    """Use the noop adapter when no explicit selection is provided."""
    monkeypatch.delenv("DPOST_SYNC_ADAPTER", raising=False)
    adapter = composition.select_sync_adapter()
    assert isinstance(adapter, NoopSyncAdapter)


def test_select_sync_adapter_supports_kadi(monkeypatch: pytest.MonkeyPatch) -> None:
    """Instantiate the kadi adapter when selected explicitly."""
    import dpost.infrastructure.sync.kadi as kadi_module

    class StubKadiSyncAdapter:
        """Synthetic kadi adapter used for deterministic selection tests."""

    monkeypatch.setattr(kadi_module, "KadiSyncAdapter", StubKadiSyncAdapter)

    adapter = composition.select_sync_adapter("kadi")

    assert isinstance(adapter, StubKadiSyncAdapter)


def test_select_sync_adapter_raises_when_kadi_dependency_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raise startup guidance when optional kadi dependency cannot be imported."""
    original_import = builtins.__import__

    def _fake_import(name: str, *args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        if name == "dpost.infrastructure.sync.kadi":
            raise ModuleNotFoundError("kadi_apy")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    with pytest.raises(RuntimeError, match="requires optional dependency 'kadi_apy'"):
        composition.select_sync_adapter("kadi")


def test_select_sync_adapter_rejects_unknown_values() -> None:
    """Raise startup errors for unknown sync adapter names."""
    with pytest.raises(RuntimeError, match="Unknown sync adapter 'mystery'"):
        composition.select_sync_adapter("mystery")


def test_select_plugin_profile_delegates_to_profile_selection() -> None:
    """Resolve optional plugin profiles through the dedicated boundary helper."""
    selected = composition.select_plugin_profile("reference")
    assert selected is REFERENCE_PLUGIN_PROFILE


def test_select_runtime_mode_resolves_valid_names(monkeypatch: pytest.MonkeyPatch) -> None:
    """Accept headless and desktop modes from both args and env values."""
    monkeypatch.setenv("DPOST_RUNTIME_MODE", "desktop")
    assert composition.select_runtime_mode() == "desktop"
    assert composition.select_runtime_mode(" headless ") == "headless"


def test_select_runtime_mode_rejects_unknown_values() -> None:
    """Raise startup errors with valid-mode guidance for invalid names."""
    with pytest.raises(RuntimeError, match="Unknown runtime mode 'custom'"):
        composition.select_runtime_mode("custom")


def test_select_ui_factory_uses_selected_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Resolve UI factory by passing selected mode into the UI-factory resolver."""
    sentinel_factory = object()
    captured_mode: dict[str, str] = {}

    monkeypatch.setattr(composition, "select_runtime_mode", lambda _mode=None: "desktop")

    def _fake_resolver(mode: str) -> object:
        captured_mode["mode"] = mode
        return sentinel_factory

    monkeypatch.setattr(composition, "resolve_ui_factory", _fake_resolver)

    resolved = composition.select_ui_factory()

    assert resolved is sentinel_factory
    assert captured_mode["mode"] == "desktop"


def test_compose_bootstrap_builds_context_from_selected_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Compose runtime context using selected sync/profile/mode/settings values."""
    sentinel_context = object()
    sentinel_sync = object()
    sentinel_profile = object()
    sentinel_settings = object()
    captured: dict[str, object] = {}

    monkeypatch.setattr(composition, "select_sync_adapter", lambda: sentinel_sync)
    monkeypatch.setattr(
        composition,
        "resolve_plugin_profile_selection",
        lambda **_kwargs: sentinel_profile,
    )
    monkeypatch.setattr(composition, "select_runtime_mode", lambda: "headless")
    monkeypatch.setattr(
        composition,
        "resolve_runtime_startup_settings",
        lambda **_kwargs: sentinel_settings,
    )

    def _fake_compose_runtime_context(**kwargs: object) -> object:
        captured.update(kwargs)
        return sentinel_context

    monkeypatch.setattr(composition, "compose_runtime_context", _fake_compose_runtime_context)

    context = composition.compose_bootstrap()

    assert context is sentinel_context
    assert captured["sync_adapter"] is sentinel_sync
    assert captured["plugin_profile"] is sentinel_profile
    assert captured["runtime_mode"] == "headless"
    assert captured["resolved_settings"] is sentinel_settings
    assert captured["ui_factory_selector"] is composition.select_ui_factory
    assert captured["startup_settings_builder"] is composition.build_startup_settings
    assert captured["runtime_bootstrap"] is composition.bootstrap_runtime
