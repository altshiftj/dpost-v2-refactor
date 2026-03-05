"""Plugin runtime host for registration, activation, and lookup APIs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from dpost_v2.application.contracts.plugin_contracts import (
    PluginContractError,
    ProcessorContract,
    validate_plugin_contract,
)
from dpost_v2.plugins.catalog import PluginCatalogSnapshot, build_catalog, get_plugin
from dpost_v2.plugins.discovery import PluginDescriptor
from dpost_v2.plugins.profile_selection import (
    PluginSelectionResult,
    select_plugins_for_profile,
)


class PluginHostError(RuntimeError):
    """Base exception for plugin host lifecycle failures."""


class PluginHostDuplicateIdError(PluginHostError):
    """Raised when host registration receives duplicate plugin ids."""


class PluginHostContractError(PluginHostError):
    """Raised when a plugin descriptor fails contract validation."""


class PluginHostActivationError(PluginHostError):
    """Raised when plugin activation or processor creation fails."""


class PluginHostShutdownError(PluginHostError):
    """Raised when plugin shutdown hooks fail."""


@dataclass(frozen=True, slots=True)
class PcDeviceScope:
    """Resolved workstation policy scope for one selected PC plugin."""

    pc_plugin_id: str
    device_plugin_ids: tuple[str, ...]
    normalized_settings: object

    def __post_init__(self) -> None:
        object.__setattr__(self, "pc_plugin_id", str(self.pc_plugin_id).strip())
        object.__setattr__(
            self,
            "device_plugin_ids",
            tuple(str(plugin_id).strip() for plugin_id in self.device_plugin_ids),
        )


class PluginHost:
    """Host for plugin registry state and lifecycle transitions."""

    def __init__(self, descriptors: Iterable[PluginDescriptor] = ()) -> None:
        self._catalog: PluginCatalogSnapshot = build_catalog(())
        self._active_plugin_ids: set[str] = set()
        if descriptors:
            self.register_descriptors(descriptors)

    @property
    def catalog(self) -> PluginCatalogSnapshot:
        """Return current immutable catalog snapshot."""
        return self._catalog

    def register_descriptors(self, descriptors: Iterable[PluginDescriptor]) -> None:
        """Register descriptors after contract re-validation gates."""
        merged: dict[str, PluginDescriptor] = {
            descriptor.plugin_id: descriptor for descriptor in self._catalog.descriptors
        }

        for descriptor in descriptors:
            if descriptor.plugin_id in merged:
                raise PluginHostDuplicateIdError(
                    f"duplicate plugin id registration: {descriptor.plugin_id}"
                )
            _validate_descriptor_contract(descriptor)
            merged[descriptor.plugin_id] = descriptor

        self._catalog = build_catalog(merged.values())

    def activate_profile(
        self,
        *,
        profile: str,
        known_profiles: Iterable[str] | None = None,
        allow_plugin_ids: Iterable[str] = (),
        deny_plugin_ids: Iterable[str] = (),
    ) -> PluginSelectionResult:
        """Activate plugins selected for one runtime profile."""
        selection = select_plugins_for_profile(
            self._catalog,
            profile=profile,
            known_profiles=known_profiles,
            allow_plugin_ids=allow_plugin_ids,
            deny_plugin_ids=deny_plugin_ids,
        )
        selected_ids = set(selection.selected_by_family["device"]) | set(
            selection.selected_by_family["pc"]
        )
        current_active = set(self._active_plugin_ids)
        removed_ids = sorted(current_active - selected_ids, reverse=True)
        added_ids = sorted(selected_ids - current_active)

        for plugin_id in removed_ids:
            descriptor = get_plugin(self._catalog, plugin_id)
            on_shutdown = descriptor.module_exports.get("on_shutdown")
            if not callable(on_shutdown):
                current_active.discard(plugin_id)
                continue
            try:
                on_shutdown()
            except Exception as exc:  # noqa: BLE001
                self._active_plugin_ids = current_active
                raise PluginHostShutdownError(
                    f"plugin {plugin_id!r} shutdown hook failed"
                ) from exc
            current_active.discard(plugin_id)

        for plugin_id in added_ids:
            descriptor = get_plugin(self._catalog, plugin_id)
            on_activate = descriptor.module_exports.get("on_activate")
            if not callable(on_activate):
                current_active.add(plugin_id)
                continue
            try:
                on_activate({"plugin_id": plugin_id, "profile": profile})
            except Exception as exc:  # noqa: BLE001
                self._active_plugin_ids = current_active
                raise PluginHostActivationError(
                    f"plugin {plugin_id!r} activation hook failed"
                ) from exc
            current_active.add(plugin_id)

        self._active_plugin_ids = current_active
        return selection

    def get_device_plugins(self, *, active_only: bool = True) -> tuple[str, ...]:
        """Return deterministic device plugin id list."""
        return self._plugins_for_family("device", active_only=active_only)

    def get_pc_plugins(self, *, active_only: bool = True) -> tuple[str, ...]:
        """Return deterministic PC plugin id list."""
        return self._plugins_for_family("pc", active_only=active_only)

    def get_by_capability(
        self,
        capability: str,
        *,
        active_only: bool = True,
    ) -> tuple[str, ...]:
        """Return plugin ids matching one capability flag."""
        candidates = self._catalog.by_capability.get(capability)
        if candidates is None:
            raise PluginHostActivationError(f"unknown capability filter: {capability}")
        plugin_ids = tuple(descriptor.plugin_id for descriptor in candidates)
        if not active_only:
            return plugin_ids
        return tuple(
            plugin_id
            for plugin_id in plugin_ids
            if plugin_id in self._active_plugin_ids
        )

    def create_device_processor(
        self,
        plugin_id: str,
        *,
        settings: Mapping[str, Any],
    ) -> ProcessorContract:
        """Build a processor from one active device plugin."""
        descriptor = get_plugin(self._catalog, plugin_id)
        if descriptor.family != "device":
            raise PluginHostActivationError(
                f"plugin {plugin_id!r} is not a device plugin"
            )
        if plugin_id not in self._active_plugin_ids:
            raise PluginHostActivationError(
                f"plugin {plugin_id!r} is not active for the current profile"
            )

        create_processor = descriptor.module_exports.get("create_processor")
        if not callable(create_processor):
            raise PluginHostActivationError(
                f"device plugin {plugin_id!r} missing create_processor export"
            )
        try:
            processor = create_processor(dict(settings))
        except Exception as exc:  # noqa: BLE001
            raise PluginHostActivationError(
                f"device plugin {plugin_id!r} failed to build processor"
            ) from exc
        if not isinstance(processor, ProcessorContract):
            raise PluginHostActivationError(
                f"device plugin {plugin_id!r} returned invalid processor contract"
            )
        return processor

    def resolve_device_scope_for_pc(
        self,
        plugin_id: str,
        *,
        settings: Mapping[str, Any] | None = None,
        active_only: bool = True,
    ) -> PcDeviceScope:
        """Resolve the device plugin ids allowed by one selected PC plugin."""
        descriptor = get_plugin(self._catalog, plugin_id)
        if descriptor.family != "pc":
            raise PluginHostActivationError(f"plugin {plugin_id!r} is not a pc plugin")
        if active_only and plugin_id not in self._active_plugin_ids:
            raise PluginHostActivationError(
                f"plugin {plugin_id!r} is not active for the current profile"
            )

        raw_settings = dict(settings or {})
        validate_settings = descriptor.module_exports.get("validate_settings")
        normalized_settings: object = raw_settings
        if callable(validate_settings):
            try:
                normalized_settings = validate_settings(raw_settings)
            except Exception as exc:  # noqa: BLE001
                raise PluginHostActivationError(
                    f"pc plugin {plugin_id!r} failed to validate settings"
                ) from exc

        configured_device_plugins = _extract_active_device_plugins(normalized_settings)
        available_device_plugins = set(self.get_device_plugins(active_only=active_only))
        scoped_device_plugins = tuple(
            sorted(
                plugin_name
                for plugin_name in configured_device_plugins
                if plugin_name in available_device_plugins
            )
        )
        return PcDeviceScope(
            pc_plugin_id=plugin_id,
            device_plugin_ids=scoped_device_plugins,
            normalized_settings=normalized_settings,
        )

    def shutdown(self) -> None:
        """Invoke shutdown hooks for active plugins and clear active state."""
        active_before = tuple(sorted(self._active_plugin_ids, reverse=True))
        for plugin_id in active_before:
            descriptor = get_plugin(self._catalog, plugin_id)
            on_shutdown = descriptor.module_exports.get("on_shutdown")
            if not callable(on_shutdown):
                continue
            try:
                on_shutdown()
            except Exception as exc:  # noqa: BLE001
                raise PluginHostShutdownError(
                    f"plugin {plugin_id!r} shutdown hook failed"
                ) from exc
        self._active_plugin_ids.clear()

    def _plugins_for_family(self, family: str, *, active_only: bool) -> tuple[str, ...]:
        plugin_ids = tuple(
            descriptor.plugin_id
            for descriptor in self._catalog.by_family[family]
            if not active_only or descriptor.plugin_id in self._active_plugin_ids
        )
        return plugin_ids


def _validate_descriptor_contract(descriptor: PluginDescriptor) -> None:
    try:
        metadata = validate_plugin_contract(descriptor.module_exports)
    except PluginContractError as exc:
        raise PluginHostContractError(
            f"plugin {descriptor.plugin_id!r} failed contract validation: {exc}"
        ) from exc

    if metadata.plugin_id != descriptor.plugin_id:
        raise PluginHostContractError(
            f"descriptor plugin id {descriptor.plugin_id!r} does not match "
            f"manifest plugin id {metadata.plugin_id!r}"
        )
    if metadata.family != descriptor.family:
        raise PluginHostContractError(
            f"descriptor family {descriptor.family!r} does not match "
            f"manifest family {metadata.family!r}"
        )


def _extract_active_device_plugins(settings: object) -> tuple[str, ...]:
    if isinstance(settings, Mapping):
        candidate = settings.get("active_device_plugins", ())
    else:
        extra = getattr(settings, "extra", None)
        if isinstance(extra, Mapping):
            candidate = extra.get("active_device_plugins", ())
        else:
            candidate = ()

    if not isinstance(candidate, tuple | list):
        return ()

    normalized: list[str] = []
    for plugin_id in candidate:
        token = str(plugin_id).strip()
        if token:
            normalized.append(token)
    return tuple(normalized)


__all__ = [
    "PcDeviceScope",
    "PluginHost",
    "PluginHostActivationError",
    "PluginHostContractError",
    "PluginHostDuplicateIdError",
    "PluginHostError",
    "PluginHostShutdownError",
]
