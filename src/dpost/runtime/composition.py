"""Composition root for dpost startup wiring."""

from __future__ import annotations

import os
from typing import Callable, Sequence

from dpost.application.ports import SyncAdapterPort
from dpost.application.services import compose_runtime_context
from dpost.infrastructure.runtime_adapters import resolve_ui_factory
from dpost.infrastructure.sync import NoopSyncAdapter
from dpost.plugins import PluginProfile
from dpost.plugins.profile_selection import resolve_plugin_profile_selection
from dpost.runtime.bootstrap import (
    BootstrapContext,
    StartupSettings,
    bootstrap_runtime,
    build_startup_settings,
    collect_startup_settings,
    startup_error,
)
from dpost.runtime.startup_config import resolve_runtime_startup_settings


def resolve_startup_settings(
    *,
    pc_name: str | None = None,
    device_names: Sequence[str] | None = None,
    prometheus_port: int | None = None,
    observability_port: int | None = None,
) -> StartupSettings | None:
    """Resolve optional startup settings from explicit overrides and env values."""
    return resolve_runtime_startup_settings(
        pc_name=pc_name,
        device_names=device_names,
        prometheus_port=prometheus_port,
        observability_port=observability_port,
        collect_settings=collect_startup_settings,
        startup_settings_builder=build_startup_settings,
        startup_error_factory=startup_error,
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
            raise startup_error(
                "Kadi sync adapter requires optional dependency 'kadi_apy'."
            ) from exc

    raise startup_error(
        f"Unknown sync adapter '{selected_name}'. Available adapters: noop, kadi."
    )


def select_plugin_profile(profile_name: str | None = None) -> PluginProfile | None:
    """Resolve the optional plugin profile used for kernel validation startup."""
    return resolve_plugin_profile_selection(
        profile_name=profile_name,
        startup_error_factory=startup_error,
    )


def select_runtime_mode(mode_name: str | None = None) -> str:
    """Resolve the runtime mode used for startup wiring."""
    selected_name = (
        (mode_name or os.getenv("DPOST_RUNTIME_MODE") or "headless").strip().lower()
    )
    if selected_name in {"headless", "desktop"}:
        return selected_name

    raise startup_error(
        "Unknown runtime mode "
        f"'{selected_name}'. Available modes: headless, desktop."
    )


def select_ui_factory(mode_name: str | None = None) -> Callable[[], object]:
    """Return the UI factory for the selected runtime mode."""
    selected_mode = select_runtime_mode(mode_name)
    return resolve_ui_factory(selected_mode)


def compose_bootstrap() -> BootstrapContext:
    """Build and return the runtime context for dpost."""

    sync_adapter = select_sync_adapter()
    plugin_profile = resolve_plugin_profile_selection(
        startup_error_factory=startup_error,
    )
    runtime_mode = select_runtime_mode()
    resolved_settings = resolve_runtime_startup_settings(
        collect_settings=collect_startup_settings,
        startup_settings_builder=build_startup_settings,
        startup_error_factory=startup_error,
    )

    return compose_runtime_context(
        sync_adapter=sync_adapter,
        plugin_profile=plugin_profile,
        runtime_mode=runtime_mode,
        resolved_settings=resolved_settings,
        ui_factory_selector=select_ui_factory,
        startup_settings_builder=build_startup_settings,
        runtime_bootstrap=bootstrap_runtime,
    )
