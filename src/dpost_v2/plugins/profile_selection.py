"""Deterministic profile-to-plugin selection policy."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType
from typing import Iterable, Mapping

from dpost_v2.plugins.catalog import PluginCatalogSnapshot


class PluginProfileError(ValueError):
    """Base exception for profile selection failures."""


class PluginProfileUnknownError(PluginProfileError):
    """Raised when runtime requests an unknown profile token."""


class PluginProfileOverrideConflictError(PluginProfileError):
    """Raised when allow and deny overrides conflict."""


class PluginProfileCatalogMismatchError(PluginProfileError):
    """Raised when override references plugin ids missing from catalog."""


class PluginProfilePolicyError(PluginProfileError):
    """Raised when profile selection policy values are malformed."""


@dataclass(frozen=True, slots=True)
class PluginSelectionResult:
    """Deterministic plugin id selection grouped by plugin family."""

    selected_by_family: Mapping[str, tuple[str, ...]]
    diagnostics: Mapping[str, Mapping[str, str]]
    fingerprint: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "selected_by_family",
            MappingProxyType(
                {
                    family: tuple(plugin_ids)
                    for family, plugin_ids in self.selected_by_family.items()
                }
            ),
        )
        object.__setattr__(
            self,
            "diagnostics",
            MappingProxyType(
                {
                    section: MappingProxyType(dict(reasons))
                    for section, reasons in self.diagnostics.items()
                }
            ),
        )


def select_plugins_for_profile(
    catalog: PluginCatalogSnapshot,
    *,
    profile: str,
    known_profiles: Iterable[str] | None = None,
    allow_plugin_ids: Iterable[str] = (),
    deny_plugin_ids: Iterable[str] = (),
) -> PluginSelectionResult:
    """Resolve enabled plugin ids for one runtime profile token."""
    normalized_profile = _normalize_profile(profile)
    known = _normalize_known_profiles(known_profiles, fallback_from_catalog=catalog)
    if normalized_profile not in known:
        raise PluginProfileUnknownError(
            f"unknown plugin profile {normalized_profile!r}; known profiles: "
            f"{', '.join(sorted(known))}"
        )

    allow = _normalize_plugin_ids(allow_plugin_ids, label="allow_plugin_ids")
    deny = _normalize_plugin_ids(deny_plugin_ids, label="deny_plugin_ids")
    overlap = allow & deny
    if overlap:
        conflicting = ", ".join(sorted(overlap))
        raise PluginProfileOverrideConflictError(
            f"plugin ids cannot be both allowed and denied: {conflicting}"
        )

    known_plugin_ids = set(catalog.by_id)
    missing = sorted((allow | deny) - known_plugin_ids)
    if missing:
        raise PluginProfileCatalogMismatchError(
            f"override references unknown plugin ids: {', '.join(missing)}"
        )

    included: dict[str, str] = {}
    excluded: dict[str, str] = {}
    selected_device: list[str] = []
    selected_pc: list[str] = []

    for descriptor in catalog.descriptors:
        plugin_id = descriptor.plugin_id
        profile_match = (
            not descriptor.supported_profiles
            or normalized_profile in descriptor.supported_profiles
        )

        if plugin_id in deny:
            excluded[plugin_id] = "deny_override"
            continue
        if plugin_id in allow:
            included[plugin_id] = "allow_override"
            if descriptor.family == "device":
                selected_device.append(plugin_id)
            else:
                selected_pc.append(plugin_id)
            continue
        if profile_match:
            included[plugin_id] = "profile_match"
            if descriptor.family == "device":
                selected_device.append(plugin_id)
            else:
                selected_pc.append(plugin_id)
            continue
        excluded[plugin_id] = "profile_mismatch"

    selected = {
        "device": tuple(sorted(selected_device)),
        "pc": tuple(sorted(selected_pc)),
    }
    diagnostics = {
        "included": dict(sorted(included.items())),
        "excluded": dict(sorted(excluded.items())),
    }
    return PluginSelectionResult(
        selected_by_family=selected,
        diagnostics=diagnostics,
        fingerprint=_selection_fingerprint(normalized_profile, selected),
    )


def _normalize_profile(profile: object) -> str:
    if not isinstance(profile, str) or not profile.strip():
        raise PluginProfilePolicyError("profile must be a non-empty string")
    return profile.strip().lower()


def _normalize_known_profiles(
    known_profiles: Iterable[str] | None,
    *,
    fallback_from_catalog: PluginCatalogSnapshot,
) -> set[str]:
    if known_profiles is None:
        from_catalog = {
            profile
            for descriptor in fallback_from_catalog.descriptors
            for profile in descriptor.supported_profiles
        }
        if from_catalog:
            return from_catalog
        return {"default"}

    normalized: set[str] = set()
    for profile in known_profiles:
        if not isinstance(profile, str) or not profile.strip():
            raise PluginProfilePolicyError(
                "known_profiles entries must be non-empty strings"
            )
        normalized.add(profile.strip().lower())
    if not normalized:
        raise PluginProfilePolicyError("known_profiles cannot be empty")
    return normalized


def _normalize_plugin_ids(plugin_ids: Iterable[str], *, label: str) -> set[str]:
    normalized: set[str] = set()
    for plugin_id in plugin_ids:
        if not isinstance(plugin_id, str) or not plugin_id.strip():
            raise PluginProfilePolicyError(f"{label} entries must be non-empty strings")
        normalized.add(plugin_id.strip())
    return normalized


def _selection_fingerprint(
    profile: str,
    selected_by_family: Mapping[str, tuple[str, ...]],
) -> str:
    hasher = sha256()
    hasher.update(profile.encode("utf-8"))
    for family in ("device", "pc"):
        ids = selected_by_family.get(family, ())
        hasher.update(f"|{family}:{','.join(ids)}".encode("utf-8"))
    return hasher.hexdigest()


__all__ = [
    "PluginProfileCatalogMismatchError",
    "PluginProfileError",
    "PluginProfileOverrideConflictError",
    "PluginProfilePolicyError",
    "PluginProfileUnknownError",
    "PluginSelectionResult",
    "select_plugins_for_profile",
]
