"""Composition root for dpost startup wiring."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Callable, Sequence

from dpost.application.ports import SyncAdapterPort
from dpost.infrastructure.runtime import HeadlessRuntimeUI
from dpost.infrastructure.sync import NoopSyncAdapter
from dpost.plugins import REFERENCE_PLUGIN_PROFILE, PluginProfile

if TYPE_CHECKING:
    from ipat_watchdog.core.app.bootstrap import BootstrapContext, StartupSettings


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
) -> int:
    """Parse and validate positive integer ports from explicit or env values."""
    if value is None:
        return fallback
    if isinstance(value, int):
        if value <= 0:
            from ipat_watchdog.core.app.bootstrap import StartupError

            raise StartupError(f"{env_name} must be a positive integer. Got {value}.")
        return value

    raw = value.strip()
    if raw == "":
        return fallback
    try:
        parsed = int(raw)
    except ValueError as exc:
        from ipat_watchdog.core.app.bootstrap import StartupError

        raise StartupError(f"Invalid integer value for {env_name}: {value!r}") from exc
    if parsed <= 0:
        from ipat_watchdog.core.app.bootstrap import StartupError

        raise StartupError(f"{env_name} must be a positive integer. Got {parsed}.")
    return parsed


def resolve_startup_settings(
    *,
    pc_name: str | None = None,
    device_names: Sequence[str] | None = None,
    prometheus_port: int | None = None,
    observability_port: int | None = None,
) -> "StartupSettings | None":
    """Resolve optional startup settings from explicit overrides and DPOST env."""
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

    from ipat_watchdog.core.app.bootstrap import (
        StartupSettings as LegacyStartupSettings,
    )
    from ipat_watchdog.core.app.bootstrap import collect_startup_settings

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

    base_settings = collect_startup_settings(
        pc_name=resolved_pc_name or None,
        device_names=resolved_device_names,
    )

    final_prometheus_port = _coerce_port(
        prometheus_port if prometheus_port is not None else env_prometheus_port,
        env_name="DPOST_PROMETHEUS_PORT",
        fallback=base_settings.prometheus_port,
    )
    final_observability_port = _coerce_port(
        (
            observability_port
            if observability_port is not None
            else env_observability_port
        ),
        env_name="DPOST_OBSERVABILITY_PORT",
        fallback=base_settings.observability_port,
    )

    return LegacyStartupSettings(
        pc_name=base_settings.pc_name,
        device_names=base_settings.device_names,
        prometheus_port=final_prometheus_port,
        observability_port=final_observability_port,
        env_source=base_settings.env_source,
    )


def select_sync_adapter(adapter_name: str | None = None) -> SyncAdapterPort:
    """Return the selected sync adapter implementation."""
    selected_name = (
        (adapter_name or os.getenv("DPOST_SYNC_ADAPTER") or "noop").strip().lower()
    )

    if selected_name == "noop":
        return NoopSyncAdapter()

    if selected_name == "kadi":
        try:
            from dpost.infrastructure.sync.kadi import KadiSyncAdapter

            return KadiSyncAdapter()
        except ModuleNotFoundError as exc:
            from ipat_watchdog.core.app.bootstrap import StartupError

            raise StartupError(
                "Kadi sync adapter requires optional dependency 'kadi_apy'."
            ) from exc

    from ipat_watchdog.core.app.bootstrap import StartupError

    raise StartupError(
        f"Unknown sync adapter '{selected_name}'. Available adapters: noop, kadi."
    )


def select_plugin_profile(profile_name: str | None = None) -> PluginProfile | None:
    """Resolve the optional plugin profile used for kernel validation startup."""
    selected_name = (
        (profile_name or os.getenv("DPOST_PLUGIN_PROFILE") or "").strip().lower()
    )
    if not selected_name:
        return None

    if selected_name == "reference":
        return REFERENCE_PLUGIN_PROFILE

    from ipat_watchdog.core.app.bootstrap import StartupError

    raise StartupError(
        "Unknown plugin profile " f"'{selected_name}'. Available profiles: reference."
    )


def select_runtime_mode(mode_name: str | None = None) -> str:
    """Resolve the runtime mode used for startup wiring."""
    selected_name = (
        (mode_name or os.getenv("DPOST_RUNTIME_MODE") or "headless").strip().lower()
    )
    if selected_name in {"headless", "desktop"}:
        return selected_name

    from ipat_watchdog.core.app.bootstrap import StartupError

    raise StartupError(
        "Unknown runtime mode "
        f"'{selected_name}'. Available modes: headless, desktop."
    )


def select_ui_factory(mode_name: str | None = None) -> Callable[[], object]:
    """Return the UI factory for the selected runtime mode."""
    selected_mode = select_runtime_mode(mode_name)
    if selected_mode == "desktop":
        from ipat_watchdog.core.ui.ui_tkinter import TKinterUI

        return TKinterUI
    return HeadlessRuntimeUI


def compose_bootstrap() -> "BootstrapContext":
    """Build and return the runtime context for dpost.

    This temporary implementation delegates to the existing ipat_watchdog
    bootstrap path while migration is in progress.
    """
    from ipat_watchdog.core.app.bootstrap import StartupSettings
    from ipat_watchdog.core.app.bootstrap import bootstrap as legacy_bootstrap

    sync_adapter = select_sync_adapter()
    plugin_profile = select_plugin_profile()
    runtime_mode = select_runtime_mode()
    resolved_settings = resolve_startup_settings()

    def sync_manager_factory(_interactions: object) -> SyncAdapterPort:
        return sync_adapter

    bootstrap_kwargs: dict[str, object] = {
        "ui_factory": select_ui_factory(runtime_mode),
        "sync_manager_factory": sync_manager_factory,
    }
    if plugin_profile is not None:
        bootstrap_kwargs["settings"] = StartupSettings(
            pc_name=plugin_profile.pc_name,
            device_names=plugin_profile.device_names,
        )
    elif resolved_settings is not None:
        bootstrap_kwargs["settings"] = resolved_settings

    return legacy_bootstrap(**bootstrap_kwargs)
