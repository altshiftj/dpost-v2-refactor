"""Unit tests for the bootstrap helpers."""

from __future__ import annotations

import pytest

import importlib

bootstrap_mod = importlib.import_module("ipat_watchdog.core.app.bootstrap")

from ipat_watchdog.core.app.bootstrap import (
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
