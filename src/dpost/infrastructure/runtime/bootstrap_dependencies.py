"""Infrastructure-owned runtime bootstrap dependencies for dpost startup."""

from __future__ import annotations

from typing import Iterable

from dpost.application.config import ConfigService, DeviceConfig, init_config
from dpost.application.runtime import DeviceWatchdogApp
from dpost.infrastructure.storage.filesystem_utils import init_dirs
from dpost.infrastructure.sync.kadi import KadiSyncAdapter
from dpost.infrastructure.runtime.desktop_ui import get_desktop_ui_class
from dpost.infrastructure.runtime.ui_adapters import (
    UiInteractionAdapter,
    UiTaskScheduler,
)
from dpost.plugins.loading import load_device_plugin, load_pc_plugin

default_ui_factory = get_desktop_ui_class()


def default_sync_manager_factory(interactions: object) -> KadiSyncAdapter:
    """Build the default sync manager through the dpost sync adapter boundary."""
    sync_manager = KadiSyncAdapter()
    sync_manager.interactions = interactions
    return sync_manager


def init_runtime_dirs() -> None:
    """Initialise runtime directory structure for the active config service."""
    init_dirs()


def build_config_service(pc_name: str, device_names: Iterable[str]) -> ConfigService:
    """Build the active config service from selected PC/device plugins."""
    pc_plugin = load_pc_plugin(pc_name)
    pc_config = pc_plugin.get_config()

    device_configs: list[DeviceConfig] = []
    for device_name in device_names:
        plugin = load_device_plugin(device_name)
        device_configs.append(plugin.get_config())

    return init_config(pc_config, device_configs)


def build_interaction_adapter(ui: object) -> UiInteractionAdapter:
    """Build the interaction adapter for the selected runtime UI object."""
    return UiInteractionAdapter(ui)


def build_scheduler(ui: object) -> UiTaskScheduler:
    """Build the task scheduler adapter for the selected runtime UI object."""
    return UiTaskScheduler(ui)


def build_watchdog_app(
    *,
    ui: object,
    sync_manager: object,
    config_service: ConfigService,
    interactions: UiInteractionAdapter,
    scheduler: UiTaskScheduler,
) -> DeviceWatchdogApp:
    """Build the watchdog runtime app from composed dependencies."""
    return DeviceWatchdogApp(
        ui=ui,
        sync_manager=sync_manager,
        config_service=config_service,
        interactions=interactions,
        scheduler=scheduler,
    )
