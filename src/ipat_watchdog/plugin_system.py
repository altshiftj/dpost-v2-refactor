"""Pluggy-based plugin management for device and PC plugins."""

from __future__ import annotations

import pkgutil
import sys
from dataclasses import dataclass
from importlib import import_module
from importlib.metadata import entry_points
from typing import Callable, Dict, Iterable, Tuple, TypeVar

import pluggy

from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.device_plugins.device_plugin import DevicePlugin
from ipat_watchdog.pc_plugins.pc_plugin import PCPlugin

logger = setup_logger(__name__)

_PLUGIN_NAMESPACE = "ipat_watchdog"
DEVICE_ENTRYPOINT_GROUP = "ipat_watchdog.device_plugins"
PC_ENTRYPOINT_GROUP = "ipat_watchdog.pc_plugins"

# Module-level singleton holder for the plugin loader
_PLUGIN_LOADER_SINGLETON: PluginLoader | None = None

hookspec = pluggy.HookspecMarker(_PLUGIN_NAMESPACE)
hookimpl = pluggy.HookimplMarker(_PLUGIN_NAMESPACE)


class HookSpecifications:
    """Hook specifications exposed to plugin modules."""

    @hookspec
    def register_device_plugins(self, registry: "DevicePluginRegistry") -> None:
        """Register device plugin factories."""

    @hookspec
    def register_pc_plugins(self, registry: "PCPluginRegistry") -> None:
        """Register PC plugin factories."""


FactoryT = TypeVar("FactoryT", bound=Callable[[], object])


@dataclass
class _BaseRegistry:
    kind: str

    def __post_init__(self) -> None:
        self._factories: Dict[str, Callable[[], object]] = {}
        # Track names we've already logged about to avoid duplicate log noise
        self._logged_names: set[str] = set()

    def clear(self) -> None:
        self._factories.clear()

    def register(self, name: str, factory: Callable[[], object]) -> None:
        normalized = name.strip()
        if not normalized:
            raise ValueError(f"{self.kind} plugin name must not be empty")
        if normalized in self._factories:
            raise ValueError(f"{self.kind} plugin '{normalized}' registered multiple times")
        self._factories[normalized] = factory
        # Only log the first time this plugin name is observed across refresh cycles
        if normalized not in self._logged_names:
            logger.debug("%s plugin '%s' registered via %s", self.kind.capitalize(), normalized, factory)
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
                f"Run `pip install ipat-watchdog[{name}]` or check casing."
            ) from exc
        plugin = factory()
        if not isinstance(plugin, DevicePlugin):
            raise TypeError(
                f"Factory for device plugin '{name}' returned {type(plugin)!r}, expected DevicePlugin"
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
                f"Run `pip install ipat-watchdog[{name}]` or check casing."
            ) from exc
        plugin = factory()
        if not isinstance(plugin, PCPlugin):
            raise TypeError(f"Factory for PC plugin '{name}' returned {type(plugin)!r}, expected PCPlugin")
        return plugin


class PluginLoader:
    """Discover and instantiate Watchdog plugins using pluggy.

    By default, plugins are loaded lazily to avoid importing every available
    plugin package at startup. Only the plugins explicitly requested by name
    will be imported and registered. Full discovery of built-ins and entry
    points can still be enabled via the constructor flags if needed for
    listing or diagnostics.
    """

    def __init__(self, *, load_entrypoints: bool = False, load_builtins: bool = False) -> None:
        self._pm = pluggy.PluginManager(_PLUGIN_NAMESPACE)
        self._pm.add_hookspecs(HookSpecifications)
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
        """Rebuild registries by invoking plugin hook implementations."""
        self._device_registry.clear()
        self._pc_registry.clear()
        self._pm.hook.register_device_plugins(registry=self._device_registry)
        self._pm.hook.register_pc_plugins(registry=self._pc_registry)

    def refresh_devices(self) -> None:
        """Rebuild only the device plugin registry.

        This avoids re-invoking PC plugin registrations when lazily loading a
        single device plugin, which previously caused duplicate-looking log
        lines even though registration remained idempotent.
        """
        self._device_registry.clear()
        self._pm.hook.register_device_plugins(registry=self._device_registry)

    def refresh_pcs(self) -> None:
        """Rebuild only the PC plugin registry.

        Used when lazily loading a PC plugin to avoid re-registering devices.
        """
        self._pc_registry.clear()
        self._pm.hook.register_pc_plugins(registry=self._pc_registry)

    def available_device_plugins(self) -> Tuple[str, ...]:
        return self._device_registry.names()

    def available_pc_plugins(self) -> Tuple[str, ...]:
        return self._pc_registry.names()

    def load_device(self, name: str) -> DevicePlugin:
        # Try existing registry first
        try:
            return self._device_registry.create(name)
        except RuntimeError:
            # Attempt lazy registration via built-in naming convention
            if self._lazy_load_builtin(DEVICE_ENTRYPOINT_GROUP, name):
                return self._device_registry.create(name)
            # Attempt lazy registration via entry points
            if self._lazy_load_entrypoint(DEVICE_ENTRYPOINT_GROUP, name):
                return self._device_registry.create(name)
            # Re-raise with original error message
            raise

    def load_pc(self, name: str) -> PCPlugin:
        # Try existing registry first
        try:
            return self._pc_registry.create(name)
        except RuntimeError:
            # Attempt lazy registration via built-in naming convention
            if self._lazy_load_builtin(PC_ENTRYPOINT_GROUP, name):
                return self._pc_registry.create(name)
            # Attempt lazy registration via entry points
            if self._lazy_load_entrypoint(PC_ENTRYPOINT_GROUP, name):
                return self._pc_registry.create(name)
            # Re-raise with original error message
            raise

    def register_plugin(self, plugin: object, name: str | None = None) -> None:
        """Register an in-memory plugin (primarily for testing) and refresh hooks."""
        try:
            self._pm.register(plugin, name=name)
        except pluggy.PluginValidationError as exc:
            raise RuntimeError(f"Plugin {plugin!r} failed validation: {exc}") from exc
        self.refresh()

    def _load_entrypoints(self, group: str) -> None:
        for entry_point in _iter_entry_points(group):
            module_name, _, _ = entry_point.value.partition(":")
            self._register_module(
                module_name=module_name,
                registration_name=f"{group}:{entry_point.name}",
                log_context=f"entry point '{entry_point.name}'",
            )
        # Refresh to collect any newly registered factories
        self.refresh()

    def _load_builtin_plugins(self) -> None:
        packages = (
            ("ipat_watchdog.device_plugins", DEVICE_ENTRYPOINT_GROUP),
            ("ipat_watchdog.pc_plugins", PC_ENTRYPOINT_GROUP),
        )
        for package_name, group in packages:
            try:
                package = import_module(package_name)
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to import plugin package '%s': %s", package_name, exc)
                continue
            package_path = getattr(package, "__path__", None)
            if not package_path:
                continue
            for module_info in pkgutil.iter_modules(package_path, prefix=f"{package_name}."):
                if not module_info.ispkg:
                    continue
                plugin_module = f"{module_info.name}.plugin"
                self._register_module(
                    module_name=plugin_module,
                    registration_name=f"builtin:{group}:{module_info.name}",
                    log_context=f"builtin plugin '{module_info.name}'",
                )
        # Refresh to collect any newly registered factories
        self.refresh()

    def _lazy_load_builtin(self, group: str, name: str) -> bool:
        """Attempt to import a single built-in plugin by naming convention.

        Returns True if the module was imported/registered successfully.
        """
        if group == DEVICE_ENTRYPOINT_GROUP:
            module_name = f"ipat_watchdog.device_plugins.{name}.plugin"
        elif group == PC_ENTRYPOINT_GROUP:
            module_name = f"ipat_watchdog.pc_plugins.{name}.plugin"
        else:
            return False

        if module_name in self._registered_modules:
            return False

        self._register_module(
            module_name=module_name,
            registration_name=f"lazy:{group}:{name}",
            log_context=f"lazy {group} plugin '{name}'",
        )
        # After a successful register, refresh only the relevant registry to invoke hookimpls
        if module_name in self._registered_modules:
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
        """Attempt to import a plugin from entry points by its name only.

        Returns True if a matching entrypoint was found and loaded.
        """
        for entry_point in _iter_entry_points(group):
            if entry_point.name != name:
                continue
            module_name, _, _ = entry_point.value.partition(":")
            self._register_module(
                module_name=module_name,
                registration_name=f"entrypoint:{group}:{name}",
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
        return False

    def _register_module(self, module_name: str, registration_name: str, log_context: str) -> None:
        if module_name in self._registered_modules:
            return
        try:
            module = import_module(module_name)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to import %s (%s): %s", module_name, log_context, exc)
            return
        # If this module object is already present in the plugin manager, skip re-registering
        # (avoids ValueError when attempting to register same module under a different name).
        if module in self._pm.get_plugins():
            self._registered_modules.add(module_name)
            return
        try:
            self._pm.register(module, name=registration_name)
        except ValueError as exc:
            # Pluggy raises ValueError if the same module is registered under a different name.
            logger.debug("Skipping duplicate registration for %s: %s", log_context, exc)
            self._registered_modules.add(module_name)
            return
        except pluggy.PluginValidationError as exc:
            logger.error("Plugin registration failed for %s: %s", log_context, exc)
            return
        # Track successfully registered module to prevent duplicate attempts from other discovery paths.
        self._registered_modules.add(module_name)

def _iter_entry_points(group: str) -> Iterable:
    """Return entry points for the given group with cross-version compatibility."""
    if sys.version_info >= (3, 10):
        # Python >= 3.10: entry_points returns EntryPoints with .select(...)
        return entry_points().select(group=group)
    # Python < 3.10: entry_points returns a mapping of groups to lists
    eps = entry_points()
    return eps.get(group, [])

def get_plugin_loader() -> PluginLoader:
    """Return the singleton plugin loader.

    Defaults to a lazy loader that only imports requested plugins.
    """
    global _PLUGIN_LOADER_SINGLETON
    if _PLUGIN_LOADER_SINGLETON is None:
        _PLUGIN_LOADER_SINGLETON = PluginLoader(load_entrypoints=False, load_builtins=False)
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
