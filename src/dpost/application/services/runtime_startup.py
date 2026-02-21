"""Application-level runtime startup orchestration for dpost composition."""

from __future__ import annotations

from typing import Callable, Protocol

from dpost.application.ports import SyncAdapterPort
from dpost.plugins import PluginProfile


class StartupSettingsBuilder(Protocol):
    """Build startup settings instances from explicit keyword arguments."""

    def __call__(self, **kwargs: object) -> object: ...


class RuntimeBootstrap(Protocol):
    """Bootstrap runtime context from composed startup wiring."""

    def __call__(self, **kwargs: object) -> object: ...


class UIFactorySelector(Protocol):
    """Resolve a mode-specific UI factory for runtime startup wiring."""

    def __call__(self, mode_name: str | None = None) -> Callable[[], object]: ...


def compose_runtime_context(
    *,
    sync_adapter: SyncAdapterPort,
    plugin_profile: PluginProfile | None,
    runtime_mode: str,
    resolved_settings: object | None,
    ui_factory_selector: UIFactorySelector,
    startup_settings_builder: StartupSettingsBuilder,
    runtime_bootstrap: RuntimeBootstrap,
) -> object:
    """Compose runtime bootstrap arguments and return a bootstrapped context."""

    def sync_manager_factory(_interactions: object) -> SyncAdapterPort:
        return sync_adapter

    bootstrap_kwargs: dict[str, object] = {
        "ui_factory": ui_factory_selector(runtime_mode),
        "sync_manager_factory": sync_manager_factory,
    }
    if plugin_profile is not None:
        bootstrap_kwargs["settings"] = startup_settings_builder(
            pc_name=plugin_profile.pc_name,
            device_names=plugin_profile.device_names,
        )
    elif resolved_settings is not None:
        bootstrap_kwargs["settings"] = resolved_settings

    return runtime_bootstrap(**bootstrap_kwargs)
