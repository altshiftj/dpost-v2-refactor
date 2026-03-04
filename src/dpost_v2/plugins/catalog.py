"""Plugin catalog snapshot and deterministic metadata lookups."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType
from typing import Iterable, Mapping

from dpost_v2.plugins.discovery import PluginDescriptor


class PluginCatalogError(RuntimeError):
    """Base exception for plugin catalog operations."""


class PluginCatalogNotFoundError(PluginCatalogError):
    """Raised when a plugin id is missing from a catalog snapshot."""


class PluginCatalogQueryError(PluginCatalogError):
    """Raised when catalog query parameters are invalid."""


class PluginCatalogDuplicateError(PluginCatalogError):
    """Raised when snapshot build receives duplicate plugin ids."""


class PluginCatalogVersionError(PluginCatalogError):
    """Raised when refresh receives a stale snapshot version token."""


@dataclass(frozen=True, slots=True)
class CatalogDiff:
    """Catalog descriptor-set delta for refresh operations."""

    added_plugin_ids: tuple[str, ...]
    removed_plugin_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PluginCatalogSnapshot:
    """Immutable plugin descriptor catalog with pre-built indexes."""

    descriptors: tuple[PluginDescriptor, ...]
    by_id: Mapping[str, PluginDescriptor]
    by_family: Mapping[str, tuple[PluginDescriptor, ...]]
    by_capability: Mapping[str, tuple[PluginDescriptor, ...]]
    by_profile: Mapping[str, tuple[PluginDescriptor, ...]]
    version: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "descriptors", tuple(self.descriptors))
        object.__setattr__(self, "by_id", MappingProxyType(dict(self.by_id)))
        object.__setattr__(self, "by_family", MappingProxyType(dict(self.by_family)))
        object.__setattr__(
            self,
            "by_capability",
            MappingProxyType(dict(self.by_capability)),
        )
        object.__setattr__(self, "by_profile", MappingProxyType(dict(self.by_profile)))


def build_catalog(descriptors: Iterable[PluginDescriptor]) -> PluginCatalogSnapshot:
    """Build an immutable catalog snapshot from validated plugin descriptors."""
    ordered = tuple(sorted(descriptors, key=lambda item: (item.plugin_id, item.family)))
    by_id: dict[str, PluginDescriptor] = {}
    for descriptor in ordered:
        if descriptor.plugin_id in by_id:
            raise PluginCatalogDuplicateError(
                f"duplicate plugin_id in catalog snapshot: {descriptor.plugin_id}"
            )
        by_id[descriptor.plugin_id] = descriptor

    by_family = {
        "device": tuple(item for item in ordered if item.family == "device"),
        "pc": tuple(item for item in ordered if item.family == "pc"),
    }
    by_capability = {
        "can_process": tuple(item for item in ordered if item.capabilities.can_process),
        "supports_preprocess": tuple(
            item for item in ordered if item.capabilities.supports_preprocess
        ),
        "supports_batch": tuple(item for item in ordered if item.capabilities.supports_batch),
        "supports_sync": tuple(item for item in ordered if item.capabilities.supports_sync),
    }
    by_profile: dict[str, tuple[PluginDescriptor, ...]] = {}
    discovered_profiles = sorted(
        {
            profile
            for descriptor in ordered
            for profile in descriptor.supported_profiles
        }
    )
    for profile in discovered_profiles:
        by_profile[profile] = tuple(
            descriptor
            for descriptor in ordered
            if not descriptor.supported_profiles or profile in descriptor.supported_profiles
        )

    return PluginCatalogSnapshot(
        descriptors=ordered,
        by_id=by_id,
        by_family=by_family,
        by_capability=by_capability,
        by_profile=by_profile,
        version=_catalog_version(ordered),
    )


def refresh_catalog(
    current: PluginCatalogSnapshot,
    new_descriptors: Iterable[PluginDescriptor],
    *,
    expected_version: str | None = None,
) -> tuple[PluginCatalogSnapshot, CatalogDiff]:
    """Refresh snapshot and return new snapshot plus descriptor diff."""
    if expected_version is not None and expected_version != current.version:
        raise PluginCatalogVersionError(
            f"stale catalog version token {expected_version!r}; current={current.version!r}"
        )

    refreshed = build_catalog(new_descriptors)
    current_ids = {descriptor.plugin_id for descriptor in current.descriptors}
    refreshed_ids = {descriptor.plugin_id for descriptor in refreshed.descriptors}
    diff = CatalogDiff(
        added_plugin_ids=tuple(sorted(refreshed_ids - current_ids)),
        removed_plugin_ids=tuple(sorted(current_ids - refreshed_ids)),
    )
    return refreshed, diff


def get_plugin(snapshot: PluginCatalogSnapshot, plugin_id: str) -> PluginDescriptor:
    """Return one descriptor by plugin id or raise catalog not-found error."""
    try:
        return snapshot.by_id[plugin_id]
    except KeyError as exc:
        raise PluginCatalogNotFoundError(f"unknown plugin_id: {plugin_id}") from exc


def query_by_family(snapshot: PluginCatalogSnapshot, family: str) -> tuple[PluginDescriptor, ...]:
    """Return descriptors for one plugin family in deterministic order."""
    normalized = family.strip().lower()
    if normalized not in {"device", "pc"}:
        raise PluginCatalogQueryError(f"unsupported plugin family: {family}")
    return snapshot.by_family[normalized]


def query_by_capability(
    snapshot: PluginCatalogSnapshot,
    capability: str,
) -> tuple[PluginDescriptor, ...]:
    """Return descriptors that declare the requested capability flag."""
    normalized = capability.strip()
    if normalized not in snapshot.by_capability:
        raise PluginCatalogQueryError(f"unsupported capability filter: {capability}")
    return snapshot.by_capability[normalized]


def _catalog_version(descriptors: Iterable[PluginDescriptor]) -> str:
    hasher = sha256()
    for descriptor in descriptors:
        profile_blob = ",".join(descriptor.supported_profiles)
        hasher.update(
            (
                f"{descriptor.plugin_id}|{descriptor.family}|{descriptor.version}|"
                f"{descriptor.contract_version}|{profile_blob}|"
                f"{descriptor.capabilities.can_process}|"
                f"{descriptor.capabilities.supports_preprocess}|"
                f"{descriptor.capabilities.supports_batch}|"
                f"{descriptor.capabilities.supports_sync}"
            ).encode("utf-8")
        )
    return hasher.hexdigest()


__all__ = [
    "CatalogDiff",
    "PluginCatalogDuplicateError",
    "PluginCatalogError",
    "PluginCatalogNotFoundError",
    "PluginCatalogQueryError",
    "PluginCatalogSnapshot",
    "PluginCatalogVersionError",
    "build_catalog",
    "get_plugin",
    "query_by_capability",
    "query_by_family",
    "refresh_catalog",
]
