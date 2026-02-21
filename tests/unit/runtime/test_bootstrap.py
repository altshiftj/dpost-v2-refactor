# ruff: noqa: E402
"""Unit tests for the bootstrap helpers."""

from __future__ import annotations

import importlib

import pytest

bootstrap_mod = importlib.import_module("dpost.runtime.bootstrap")
from dpost.runtime.bootstrap import (
    collect_startup_settings,
    MissingConfiguration,
    StartupError,
)


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    for key in ("PC_NAME", "DEVICE_PLUGINS", "PROMETHEUS_PORT", "OBSERVABILITY_PORT"):
        monkeypatch.delenv(key, raising=False)
    yield


def test_collect_startup_settings_requires_pc_name():
    with pytest.raises(MissingConfiguration):
        collect_startup_settings(load_env=False)


def test_collect_startup_settings_reads_device_list(monkeypatch):
    monkeypatch.setenv("PC_NAME", "test_pc")
    monkeypatch.setenv("DEVICE_PLUGINS", "dev1; dev2, dev3")
    monkeypatch.setenv("PROMETHEUS_PORT", "9000")
    monkeypatch.setenv("OBSERVABILITY_PORT", "9100")

    settings = collect_startup_settings(load_env=False)

    assert settings.pc_name == "test_pc"
    assert settings.device_names == ("dev1", "dev2", "dev3")
    assert settings.prometheus_port == 9000
    assert settings.observability_port == 9100


def test_collect_startup_settings_infers_devices(monkeypatch):
    monkeypatch.setenv("PC_NAME", "pc-a")
    monkeypatch.setenv("DEVICE_PLUGINS", "")
    monkeypatch.setenv("PROMETHEUS_PORT", "8000")
    monkeypatch.setenv("OBSERVABILITY_PORT", "8001")

    monkeypatch.setattr(
        bootstrap_mod,
        "get_devices_for_pc",
        lambda pc: [f"{pc}-camera"],
    )

    settings = collect_startup_settings(load_env=False)
    assert settings.device_names == ("pc-a-camera",)


def test_collect_startup_settings_rejects_invalid_port(monkeypatch):
    monkeypatch.setenv("PC_NAME", "pc-a")
    monkeypatch.setenv("PROMETHEUS_PORT", "not-an-int")
    monkeypatch.setattr(bootstrap_mod, "get_devices_for_pc", lambda _pc: ["device"])

    with pytest.raises(StartupError):
        collect_startup_settings(load_env=False)


def test_collect_startup_settings_rejects_negative_port(monkeypatch):
    monkeypatch.setenv("PC_NAME", "pc-a")
    monkeypatch.setenv("PROMETHEUS_PORT", "-1")
    monkeypatch.setattr(bootstrap_mod, "get_devices_for_pc", lambda _pc: ["device"])

    with pytest.raises(StartupError):
        collect_startup_settings(load_env=False)


def test_collect_startup_settings_requires_devices(monkeypatch):
    monkeypatch.setenv("PC_NAME", "pc-a")
    monkeypatch.setenv("DEVICE_PLUGINS", "")
    monkeypatch.setattr(bootstrap_mod, "get_devices_for_pc", lambda _pc: [])

    with pytest.raises(MissingConfiguration):
        collect_startup_settings(load_env=False)


def test_load_bundled_env_reads_file(monkeypatch, tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("PC_NAME=demo_pc\n", encoding="utf-8")
    monkeypatch.delenv("PC_NAME", raising=False)

    result = bootstrap_mod.load_bundled_env(bundle_dir=tmp_path)

    assert result == env_path
    assert bootstrap_mod.os.getenv("PC_NAME") == "demo_pc"


def test_build_config_service_uses_plugins(monkeypatch):
    sentinel_config = object()
    calls: dict[str, object] = {}

    def build_config_service(pc_name, device_names):
        calls["pc_name"] = pc_name
        calls["device_names"] = tuple(device_names)
        return sentinel_config

    monkeypatch.setattr(bootstrap_mod, "_build_config_service", build_config_service)

    config = bootstrap_mod._build_config_service("pc", ["dev1", "dev2"])
    assert config is sentinel_config
    assert calls["pc_name"] == "pc"
    assert calls["device_names"] == ("dev1", "dev2")


def test_bootstrap_starts_services(monkeypatch):
    settings = bootstrap_mod.StartupSettings(
        pc_name="pc",
        device_names=("dev1",),
        prometheus_port=9101,
        observability_port=9102,
    )

    calls = {"prom": None, "obs": None, "init_dirs": 0}

    monkeypatch.setattr(bootstrap_mod, "_build_config_service", lambda *_: "config")
    monkeypatch.setattr(bootstrap_mod, "init_dirs", lambda: calls.__setitem__("init_dirs", calls["init_dirs"] + 1))
    monkeypatch.setattr(bootstrap_mod, "start_http_server", lambda port: calls.__setitem__("prom", port))
    monkeypatch.setattr(bootstrap_mod, "start_observability_server", lambda port: calls.__setitem__("obs", port))
    monkeypatch.setattr(
        bootstrap_mod,
        "DeviceWatchdogApp",
        lambda **kwargs: type("AppStub", (), {"run": lambda self: None})(),
    )

    ui_stub = type("UIStub", (), {})()
    monkeypatch.setattr(bootstrap_mod, "UiInteractionAdapter", lambda ui: f"adapter:{ui}")
    monkeypatch.setattr(bootstrap_mod, "UiTaskScheduler", lambda ui: f"scheduler:{ui}")

    context = bootstrap_mod.bootstrap(
        settings=settings,
        ui_factory=lambda: ui_stub,
        sync_manager_factory=lambda adapter: f"sync:{adapter}",
    )

    assert calls["prom"] == 9101
    assert calls["obs"] == 9102
    assert calls["init_dirs"] == 1
    assert context.config_service == "config"
