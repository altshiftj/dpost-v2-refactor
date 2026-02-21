"""Unit coverage for runtime startup-config resolution helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from dpost.runtime.startup_config import (
    _coerce_port,
    _list_from_env,
    resolve_runtime_startup_settings,
)


class StartupConfigError(RuntimeError):
    """Raised by test startup-error factories for branch verification."""


@dataclass(frozen=True)
class _Settings:
    """Lightweight stand-in for runtime startup settings."""

    pc_name: str
    device_names: tuple[str, ...]
    prometheus_port: int
    observability_port: int
    env_source: Path | None = None


def test_list_from_env_supports_comma_semicolon_and_trimming() -> None:
    """Normalize mixed delimiters and whitespace into clean token tuples."""
    parsed = _list_from_env(" dev1 ;dev2, dev3 ,, ; ")
    assert parsed == ("dev1", "dev2", "dev3")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, 7000),
        ("", 7000),
        ("   ", 7000),
        ("9100", 9100),
        (9200, 9200),
    ],
)
def test_coerce_port_accepts_valid_values_and_fallbacks(
    value: int | str | None,
    expected: int,
) -> None:
    """Return parsed positive ports or provided fallback defaults."""
    port = _coerce_port(
        value,
        env_name="DPOST_PROMETHEUS_PORT",
        fallback=7000,
        startup_error_factory=StartupConfigError,
    )

    assert port == expected


@pytest.mark.parametrize(
    ("value", "pattern"),
    [
        (-1, "must be a positive integer"),
        ("0", "must be a positive integer"),
        ("not-an-int", "Invalid integer value"),
    ],
)
def test_coerce_port_rejects_invalid_values(
    value: int | str,
    pattern: str,
) -> None:
    """Raise startup errors for non-positive or non-integer values."""
    with pytest.raises(StartupConfigError, match=pattern):
        _coerce_port(
            value,
            env_name="DPOST_OBSERVABILITY_PORT",
            fallback=7100,
            startup_error_factory=StartupConfigError,
        )


def test_resolve_runtime_startup_settings_returns_none_without_any_overrides() -> None:
    """Return ``None`` when no explicit values and no related env vars are set."""
    collect_calls = 0

    def _collect_settings(**_kwargs: object) -> _Settings:
        nonlocal collect_calls
        collect_calls += 1
        return _Settings("unused", ("unused",), 8000, 8001)

    resolved = resolve_runtime_startup_settings(
        collect_settings=_collect_settings,
        startup_settings_builder=lambda **kwargs: _Settings(**kwargs),
        startup_error_factory=StartupConfigError,
    )

    assert resolved is None
    assert collect_calls == 0


def test_resolve_runtime_startup_settings_uses_explicit_overrides() -> None:
    """Use explicit inputs and filter empty device names before collect/build."""
    collect_kwargs: dict[str, object] = {}
    build_kwargs: dict[str, object] = {}

    def _collect_settings(**kwargs: object) -> _Settings:
        collect_kwargs.update(kwargs)
        return _Settings(
            pc_name="resolved-pc",
            device_names=("resolved-device",),
            prometheus_port=8000,
            observability_port=8001,
            env_source=None,
        )

    def _build_settings(**kwargs: object) -> _Settings:
        build_kwargs.update(kwargs)
        return _Settings(**kwargs)

    resolved = resolve_runtime_startup_settings(
        pc_name=" explicit-pc ",
        device_names=("dev-a", " ", "dev-b"),
        prometheus_port=9100,
        observability_port=9200,
        collect_settings=_collect_settings,
        startup_settings_builder=_build_settings,
        startup_error_factory=StartupConfigError,
    )

    assert collect_kwargs == {
        "pc_name": "explicit-pc",
        "device_names": ("dev-a", "dev-b"),
    }
    assert resolved == _Settings(
        pc_name="resolved-pc",
        device_names=("resolved-device",),
        prometheus_port=9100,
        observability_port=9200,
        env_source=None,
    )
    assert build_kwargs["prometheus_port"] == 9100
    assert build_kwargs["observability_port"] == 9200


def test_resolve_runtime_startup_settings_reads_env_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resolve startup values from environment when explicit args are missing."""
    monkeypatch.setenv("DPOST_PC_NAME", "pc-env")
    monkeypatch.setenv("DPOST_DEVICE_PLUGINS", "dev1; dev2")
    monkeypatch.setenv("DPOST_PROMETHEUS_PORT", "9010")
    monkeypatch.setenv("DPOST_OBSERVABILITY_PORT", "9020")

    collected: dict[str, object] = {}

    def _collect_settings(**kwargs: object) -> _Settings:
        collected.update(kwargs)
        return _Settings(
            pc_name="base-pc",
            device_names=("base-device",),
            prometheus_port=8000,
            observability_port=8001,
            env_source=None,
        )

    resolved = resolve_runtime_startup_settings(
        collect_settings=_collect_settings,
        startup_settings_builder=lambda **kwargs: _Settings(**kwargs),
        startup_error_factory=StartupConfigError,
    )

    assert collected == {"pc_name": "pc-env", "device_names": ("dev1", "dev2")}
    assert resolved is not None
    assert resolved.prometheus_port == 9010
    assert resolved.observability_port == 9020


def test_resolve_runtime_startup_settings_raises_on_invalid_env_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail fast when env port values cannot be parsed as positive integers."""
    monkeypatch.setenv("DPOST_PC_NAME", "pc-env")
    monkeypatch.setenv("DPOST_PROMETHEUS_PORT", "invalid-port")

    with pytest.raises(StartupConfigError, match="Invalid integer value"):
        resolve_runtime_startup_settings(
            collect_settings=lambda **_kwargs: _Settings("pc", ("dev",), 8000, 8001),
            startup_settings_builder=lambda **kwargs: _Settings(**kwargs),
            startup_error_factory=StartupConfigError,
        )
