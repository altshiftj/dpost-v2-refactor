"""Runtime startup settings resolution boundary for dpost startup config."""

from __future__ import annotations

import os
from typing import Callable, Sequence

from dpost.runtime.bootstrap import StartupSettings


def _list_from_env(raw: str) -> tuple[str, ...]:
    """Normalize comma/semicolon delimited env values into a token tuple."""
    return tuple(
        token.strip() for token in raw.replace(";", ",").split(",") if token.strip()
    )


def _coerce_port(
    value: int | str | None,
    *,
    env_name: str,
    fallback: int,
    startup_error_factory: Callable[[str], Exception],
) -> int:
    """Parse and validate positive integer ports from explicit or env values."""
    if value is None:
        return fallback
    if isinstance(value, int):
        if value <= 0:
            raise startup_error_factory(
                f"{env_name} must be a positive integer. Got {value}."
            )
        return value

    raw = value.strip()
    if raw == "":
        return fallback
    try:
        parsed = int(raw)
    except ValueError as exc:
        raise startup_error_factory(
            f"Invalid integer value for {env_name}: {value!r}"
        ) from exc
    if parsed <= 0:
        raise startup_error_factory(
            f"{env_name} must be a positive integer. Got {parsed}."
        )
    return parsed


def resolve_runtime_startup_settings(
    *,
    pc_name: str | None = None,
    device_names: Sequence[str] | None = None,
    prometheus_port: int | None = None,
    observability_port: int | None = None,
    collect_settings: Callable[..., StartupSettings],
    startup_settings_builder: Callable[..., StartupSettings],
    startup_error_factory: Callable[[str], Exception],
) -> StartupSettings | None:
    """Resolve optional startup settings from explicit overrides and env vars."""
    env_pc_name = os.getenv("DPOST_PC_NAME")
    env_device_names = os.getenv("DPOST_DEVICE_PLUGINS")
    env_prometheus_port = os.getenv("DPOST_PROMETHEUS_PORT")
    env_observability_port = os.getenv("DPOST_OBSERVABILITY_PORT")

    has_overrides = any(
        (
            pc_name is not None,
            device_names is not None,
            prometheus_port is not None,
            observability_port is not None,
            bool(env_pc_name and env_pc_name.strip()),
            bool(env_device_names and env_device_names.strip()),
            bool(env_prometheus_port and env_prometheus_port.strip()),
            bool(env_observability_port and env_observability_port.strip()),
        )
    )
    if not has_overrides:
        return None

    resolved_pc_name = (pc_name if pc_name is not None else (env_pc_name or "")).strip()
    resolved_device_names: tuple[str, ...] | None
    if device_names is not None:
        resolved_device_names = tuple(
            name.strip() for name in device_names if name.strip()
        )
    elif env_device_names:
        resolved_device_names = _list_from_env(env_device_names)
    else:
        resolved_device_names = None

    base_settings = collect_settings(
        pc_name=resolved_pc_name or None,
        device_names=resolved_device_names,
    )

    final_prometheus_port = _coerce_port(
        prometheus_port if prometheus_port is not None else env_prometheus_port,
        env_name="DPOST_PROMETHEUS_PORT",
        fallback=base_settings.prometheus_port,
        startup_error_factory=startup_error_factory,
    )
    final_observability_port = _coerce_port(
        (
            observability_port
            if observability_port is not None
            else env_observability_port
        ),
        env_name="DPOST_OBSERVABILITY_PORT",
        fallback=base_settings.observability_port,
        startup_error_factory=startup_error_factory,
    )

    return startup_settings_builder(
        pc_name=base_settings.pc_name,
        device_names=base_settings.device_names,
        prometheus_port=final_prometheus_port,
        observability_port=final_observability_port,
        env_source=base_settings.env_source,
    )
