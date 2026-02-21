"""Additional unit coverage for runtime bootstrap helper branches."""

from __future__ import annotations

import builtins
import importlib
from pathlib import Path
from unittest.mock import Mock

import dpost.runtime.bootstrap as bootstrap_mod


def test_bootstrap_runtime_delegates_to_bootstrap(monkeypatch) -> None:
    """Forward keyword arguments directly to ``bootstrap`` helper."""
    sentinel_context = object()
    captured_kwargs: dict[str, object] = {}

    def _fake_bootstrap(**kwargs: object) -> object:
        captured_kwargs.update(kwargs)
        return sentinel_context

    monkeypatch.setattr(bootstrap_mod, "bootstrap", _fake_bootstrap)

    context = bootstrap_mod.bootstrap_runtime(settings="settings")

    assert context is sentinel_context
    assert captured_kwargs == {"settings": "settings"}


def test_build_startup_settings_constructs_settings_dataclass() -> None:
    """Build startup settings via the exported contract helper."""
    settings = bootstrap_mod.build_startup_settings(
        pc_name="pc-main",
        device_names=("dev-a",),
        prometheus_port=9000,
        observability_port=9001,
        env_source=None,
    )

    assert isinstance(settings, bootstrap_mod.StartupSettings)
    assert settings.pc_name == "pc-main"
    assert settings.device_names == ("dev-a",)


def test_load_bundled_env_returns_none_when_file_missing(tmp_path: Path) -> None:
    """Return ``None`` when no bundled `.env` file exists."""
    env_source = bootstrap_mod.load_bundled_env(bundle_dir=tmp_path)
    assert env_source is None


def test_resolve_bundle_dir_prefers_meipass_when_frozen(monkeypatch) -> None:
    """Use ``sys._MEIPASS`` bundle root when running in frozen mode."""
    monkeypatch.setattr(bootstrap_mod.sys, "frozen", True, raising=False)
    monkeypatch.setattr(
        bootstrap_mod.sys,
        "_MEIPASS",
        str(Path("C:/bundle/root")),
        raising=False,
    )

    resolved = bootstrap_mod._resolve_bundle_dir()  # noqa: SLF001

    assert resolved == Path("C:/bundle/root")


def test_resolve_bundle_dir_falls_back_to_parent_when_depth_is_short(
    monkeypatch,
) -> None:
    """Fallback to module parent when parent-depth indexing raises IndexError."""

    class _ResolvedPath:
        def __init__(self) -> None:
            self.parents = [Path("C:/only-parent")]
            self.parent = Path("C:/fallback-parent")

    class _PathInput:
        def resolve(self) -> _ResolvedPath:
            return _ResolvedPath()

    monkeypatch.setattr(bootstrap_mod, "Path", lambda *_args, **_kwargs: _PathInput())
    monkeypatch.setattr(bootstrap_mod.sys, "frozen", False, raising=False)

    resolved = bootstrap_mod._resolve_bundle_dir()  # noqa: SLF001

    assert resolved == Path("C:/fallback-parent")


def test_coerce_port_returns_default_for_blank_values() -> None:
    """Fallback to default port for blank-string environment values."""
    assert (
        bootstrap_mod._coerce_port("   ", bootstrap_mod.DEFAULT_PROMETHEUS_PORT, "PORT")  # noqa: SLF001
        == bootstrap_mod.DEFAULT_PROMETHEUS_PORT
    )


def test_bootstrap_warns_when_observability_server_is_unavailable(monkeypatch) -> None:
    """Log warning branch when observability optional dependency is unavailable."""
    settings = bootstrap_mod.StartupSettings(
        pc_name="pc",
        device_names=("dev",),
        prometheus_port=9101,
        observability_port=9102,
    )
    logger = Mock()
    ui = object()
    app = object()

    monkeypatch.setattr(bootstrap_mod, "_build_config_service", lambda *_: "config")
    monkeypatch.setattr(bootstrap_mod, "init_dirs", lambda: None)
    monkeypatch.setattr(bootstrap_mod, "start_http_server", lambda _port: None)
    monkeypatch.setattr(bootstrap_mod, "start_observability_server", None)
    monkeypatch.setattr(
        bootstrap_mod,
        "_OBSERVABILITY_IMPORT_ERROR",
        ModuleNotFoundError("simulated missing dependency"),
    )
    monkeypatch.setattr(bootstrap_mod, "UiInteractionAdapter", lambda _ui: "interactions")
    monkeypatch.setattr(bootstrap_mod, "UiTaskScheduler", lambda _ui: "scheduler")
    monkeypatch.setattr(
        bootstrap_mod,
        "DeviceWatchdogApp",
        lambda **_kwargs: app,
    )
    monkeypatch.setattr(bootstrap_mod, "logger", logger)

    context = bootstrap_mod.bootstrap(
        settings=settings,
        ui_factory=lambda: ui,
        sync_manager_factory=lambda _adapter: "sync-manager",
    )

    assert context.config_service == "config"
    assert context.app is app
    logger.warning.assert_called_once()


def test_bootstrap_import_sets_observability_fallback_when_module_is_missing() -> None:
    """Cover import-time fallback that disables observability integration."""
    real_import = builtins.__import__

    def _fake_import(name: str, *args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        if name == "dpost.infrastructure.observability":
            raise ModuleNotFoundError("missing observability module")
        return real_import(name, *args, **kwargs)

    module = importlib.import_module("dpost.runtime.bootstrap")

    try:
        builtins.__import__ = _fake_import
        reloaded = importlib.reload(module)
        assert reloaded.start_observability_server is None
        assert isinstance(reloaded._OBSERVABILITY_IMPORT_ERROR, ModuleNotFoundError)
    finally:
        builtins.__import__ = real_import
        importlib.reload(module)
