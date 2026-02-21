"""Pluggy-based plugin management for canonical dpost plugin loading."""

from __future__ import annotations

import pkgutil
import sys
from dataclasses import dataclass
from importlib import import_module
from importlib.metadata import entry_points
from typing import Callable, Dict, Iterable, Tuple, TypeVar

import pluggy

from dpost.infrastructure.logging import setup_logger
from dpost.plugins.contracts import DevicePlugin, PCPlugin
from dpost.plugins.legacy_compat import (
    LEGACY_PLUGIN_NAMESPACE,
    legacy_builtin_module_name,
    legacy_builtin_packages,
    legacy_entrypoint_groups,
)

logger = setup_logger(__name__)

_PLUGIN_NAMESPACE = "dpost"
DEVICE_ENTRYPOINT_GROUP = "dpost.device_plugins"
PC_ENTRYPOINT_GROUP = "dpost.pc_plugins"

_PLUGIN_LOADER_SINGLETON: PluginLoader | None = None

hookspec = pluggy.HookspecMarker(_PLUGIN_NAMESPACE)
hookimpl = pluggy.HookimplMarker(_PLUGIN_NAMESPACE)
_legacy_hookspec = pluggy.HookspecMarker(LEGACY_PLUGIN_NAMESPACE)


class HookSpecifications:
    """Hook specifications exposed to plugin modules."""

    @hookspec
    def register_device_plugins(self, registry: "DevicePluginRegistry") -> None:
        """Register device plugin factories."""

    @hookspec
    def register_pc_plugins(self, registry: "PCPluginRegistry") -> None:
        """Register PC plugin factories."""


class LegacyHookSpecifications:
    """Legacy hook specifications kept for transition compatibility."""

    @_legacy_hookspec
    def register_device_plugins(self, registry: "DevicePluginRegistry") -> None:
        """Register device plugin factories via legacy marker namespace."""

    @_legacy_hookspec
    def register_pc_plugins(self, registry: "PCPluginRegistry") -> None:
        """Register PC plugin factories via legacy marker namespace."""


FactoryT = TypeVar("FactoryT", bound=Callable[[], object])


@dataclass
class _BaseRegistry:
    kind: str

    def __post_init__(self) -> None:
        self._factories: Dict[str, Callable[[], object]] = {}
        self._logged_names: set[str] = set()

    def clear(self) -> None:
        self._factories.clear()

    def register(self, name: str, factory: Callable[[], object]) -> None:
        normalized = name.strip()
        if not normalized:
            raise ValueError(f"{self.kind} plugin name must not be empty")
        if normalized in self._factories:
            raise ValueError(
                f"{self.kind} plugin '{normalized}' registered multiple times"
            )
        self._factories[normalized] = factory
        if normalized not in self._logged_names:
            logger.debug(
                "%s plugin '%s' registered via %s",
                self.kind.capitalize(),
                normalized,
                factory,
            )
            self._logged_names.add(normalized)

    def names(self) -> Tuple[str, ...]:
        return tuple(self._factories.keys())


class DevicePluginRegistry(_BaseRegistry):
    def __init__(self) -> None:
        super().__init__(kind="device")

    def create(self, name: str) -> DevicePlugin:
        try:
            factory = self._factories[name]
        except KeyError as exc:
            available_plugins = ", ".join(sorted(self._factories)) or "(none)"
            raise RuntimeError(
                f"No device plugin named {name!r} installed. "
                f"Available device plugins: {available_plugins}. "
                f"Run `pip install dpost[{name}]` or check casing."
            ) from exc
        plugin = factory()
        if not isinstance(plugin, DevicePlugin):
            raise TypeError(
                f"Factory for device plugin '{name}' returned {type(plugin)!r}, "
                "expected DevicePlugin"
            )
        return plugin


class PCPluginRegistry(_BaseRegistry):
    def __init__(self) -> None:
        super().__init__(kind="pc")

    def create(self, name: str) -> PCPlugin:
        try:
            factory = self._factories[name]
        except KeyError as exc:
            available_plugins = ", ".join(sorted(self._factories)) or "(none)"
            raise RuntimeError(
                f"No PC plugin named {name!r} installed. "
                f"Available PC plugins: {available_plugins}. "
                f"Run `pip install dpost[{name}]` or check casing."
            ) from exc
        plugin = factory()
        if not isinstance(plugin, PCPlugin):
            raise TypeError(
                f"Factory for PC plugin '{name}' returned {type(plugin)!r}, "
                "expected PCPlugin"
            )
        return plugin


class PluginLoader:
    """Discover and instantiate plugins with lazy-loading by default."""

    def __init__(
        self, *, load_entrypoints: bool = False, load_builtins: bool = False
    ) -> None:
        self._pm = pluggy.PluginManager(_PLUGIN_NAMESPACE)
        self._legacy_pm = pluggy.PluginManager(LEGACY_PLUGIN_NAMESPACE)
        self._pm.add_hookspecs(HookSpecifications)
        self._legacy_pm.add_hookspecs(LegacyHookSpecifications)
        self._device_registry = DevicePluginRegistry()
        self._pc_registry = PCPluginRegistry()
        self._registered_modules: set[str] = set()
        if load_builtins:
            self._load_builtin_plugins()
        if load_entrypoints:
            self._load_entrypoints(DEVICE_ENTRYPOINT_GROUP)
            self._load_entrypoints(PC_ENTRYPOINT_GROUP)
        self.refresh()

    def refresh(self) -> None:
        self._device_registry.clear()
        self._pc_registry.clear()
        self._invoke_registration_hooks(devices=True, pcs=True)

    def refresh_devices(self) -> None:
        self._device_registry.clear()
        self._invoke_registration_hooks(devices=True, pcs=False)

    def refresh_pcs(self) -> None:
        self._pc_registry.clear()
        self._invoke_registration_hooks(devices=False, pcs=True)

    def available_device_plugins(self) -> Tuple[str, ...]:
        return self._device_registry.names()

    def available_pc_plugins(self) -> Tuple[str, ...]:
        return self._pc_registry.names()

    def load_device(self, name: str) -> DevicePlugin:
        try:
            return self._device_registry.create(name)
        except RuntimeError:
            if self._lazy_load_builtin(DEVICE_ENTRYPOINT_GROUP, name):
                return self._device_registry.create(name)
            if self._lazy_load_entrypoint(DEVICE_ENTRYPOINT_GROUP, name):
                return self._device_registry.create(name)
            if not self._device_registry.names():
                self._load_builtin_plugins()
            return self._device_registry.create(name)

    def load_pc(self, name: str) -> PCPlugin:
        try:
            return self._pc_registry.create(name)
        except RuntimeError:
            if self._lazy_load_builtin(PC_ENTRYPOINT_GROUP, name):
                return self._pc_registry.create(name)
            if self._lazy_load_entrypoint(PC_ENTRYPOINT_GROUP, name):
                return self._pc_registry.create(name)
            if not self._pc_registry.names():
                self._load_builtin_plugins()
            return self._pc_registry.create(name)

    def register_plugin(self, plugin: object, name: str | None = None) -> None:
        try:
            self._pm.register(plugin, name=name)
            self._legacy_pm.register(
                plugin,
                name=f"legacy:{name}" if name is not None else None,
            )
        except pluggy.PluginValidationError as exc:
            raise RuntimeError(f"Plugin {plugin!r} failed validation: {exc}") from exc
        self.refresh()

    def _invoke_registration_hooks(self, *, devices: bool, pcs: bool) -> None:
        for plugin_manager in (self._pm, self._legacy_pm):
            if devices:
                plugin_manager.hook.register_device_plugins(
                    registry=self._device_registry
                )
            if pcs:
                plugin_manager.hook.register_pc_plugins(registry=self._pc_registry)

    def _load_entrypoints(self, group: str) -> None:
        groups = (group, *legacy_entrypoint_groups(group))
        for selected_group in groups:
            for entry_point in _iter_entry_points(selected_group):
                module_name, _, _ = entry_point.value.partition(":")
                self._register_module(
                    module_name=module_name,
                    registration_name=f"{selected_group}:{entry_point.name}",
                    log_context=f"entry point '{entry_point.name}'",
                )
        self.refresh()

    def _load_builtin_plugins(self) -> None:
        packages = (
            ("dpost.device_plugins", DEVICE_ENTRYPOINT_GROUP),
            ("dpost.pc_plugins", PC_ENTRYPOINT_GROUP),
            *legacy_builtin_packages(),
        )
        for package_name, group in packages:
            try:
                package = import_module(package_name)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Failed to import plugin package '%s': %s", package_name, exc
                )
                continue
            package_path = getattr(package, "__path__", None)
            if not package_path:
                continue
            for module_info in pkgutil.iter_modules(
                package_path, prefix=f"{package_name}."
            ):
                if not module_info.ispkg:
                    continue
                plugin_module = f"{module_info.name}.plugin"
                self._register_module(
                    module_name=plugin_module,
                    registration_name=f"builtin:{group}:{module_info.name}",
                    log_context=f"builtin plugin '{module_info.name}'",
                )
        self.refresh()

    def _lazy_load_builtin(self, group: str, name: str) -> bool:
        if group == DEVICE_ENTRYPOINT_GROUP:
            module_name = f"dpost.device_plugins.{name}.plugin"
        elif group == PC_ENTRYPOINT_GROUP:
            module_name = f"dpost.pc_plugins.{name}.plugin"
        else:
            return False

        module_candidates = [module_name]
        legacy_module_name = legacy_builtin_module_name(group, name)
        if legacy_module_name is not None:
            module_candidates.append(legacy_module_name)

        for candidate_name in module_candidates:
            if candidate_name in self._registered_modules:
                continue

            self._register_module(
                module_name=candidate_name,
                registration_name=f"lazy:{group}:{name}",
                log_context=f"lazy {group} plugin '{name}'",
            )
            if candidate_name in self._registered_modules:
                if group == DEVICE_ENTRYPOINT_GROUP:
                    self.refresh_devices()
                else:
                    self.refresh_pcs()
                logger.debug(
                    "Lazily loaded %s plugin '%s'",
                    "device" if group == DEVICE_ENTRYPOINT_GROUP else "pc",
                    name,
                )
                return True
        return False

    def _lazy_load_entrypoint(self, group: str, name: str) -> bool:
        groups = (group, *legacy_entrypoint_groups(group))
        for selected_group in groups:
            for entry_point in _iter_entry_points(selected_group):
                if entry_point.name != name:
                    continue
                module_name, _, _ = entry_point.value.partition(":")
                self._register_module(
                    module_name=module_name,
                    registration_name=f"entrypoint:{selected_group}:{name}",
                    log_context=f"entry point '{name}'",
                )
                if module_name in self._registered_modules:
                    if group == DEVICE_ENTRYPOINT_GROUP:
                        self.refresh_devices()
                    else:
                        self.refresh_pcs()
                    logger.debug(
                        "Lazily loaded %s plugin '%s' via entry point",
                        "device" if group == DEVICE_ENTRYPOINT_GROUP else "pc",
                        name,
                    )
                    return True
        return False

    def _register_module(
        self, module_name: str, registration_name: str, log_context: str
    ) -> None:
        if module_name in self._registered_modules:
            return
        try:
            module = import_module(module_name)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to import %s (%s): %s", module_name, log_context, exc)
            return
        registered = False
        plugin_managers = (
            (self._pm, "dpost"),
            (self._legacy_pm, "legacy"),
        )
        for plugin_manager, manager_name in plugin_managers:
            if module in plugin_manager.get_plugins():
                registered = True
                continue
            try:
                plugin_manager.register(
                    module, name=f"{manager_name}:{registration_name}"
                )
            except ValueError as exc:
                logger.debug(
                    "Skipping duplicate registration for %s (%s): %s",
                    log_context,
                    manager_name,
                    exc,
                )
                registered = True
            except pluggy.PluginValidationError as exc:
                logger.error(
                    "Plugin registration failed for %s (%s): %s",
                    log_context,
                    manager_name,
                    exc,
                )
            else:
                registered = True
        if registered:
            self._registered_modules.add(module_name)


def _iter_entry_points(group: str) -> Iterable:
    """Return entry points for the given group with cross-version compatibility."""
    if sys.version_info >= (3, 10):
        return entry_points().select(group=group)
    eps = entry_points()
    return eps.get(group, [])


def get_plugin_loader() -> PluginLoader:
    """Return the singleton plugin loader used by dpost plugin boundaries."""
    global _PLUGIN_LOADER_SINGLETON
    if _PLUGIN_LOADER_SINGLETON is None:
        _PLUGIN_LOADER_SINGLETON = PluginLoader(
            load_entrypoints=False,
            load_builtins=False,
        )
    return _PLUGIN_LOADER_SINGLETON


__all__ = [
    "DEVICE_ENTRYPOINT_GROUP",
    "PC_ENTRYPOINT_GROUP",
    "DevicePluginRegistry",
    "PCPluginRegistry",
    "PluginLoader",
    "get_plugin_loader",
    "hookimpl",
    "hookspec",
]
