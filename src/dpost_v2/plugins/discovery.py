"""Deterministic plugin discovery and descriptor normalization."""

from __future__ import annotations

import pkgutil
from dataclasses import dataclass
from hashlib import sha256
from importlib import import_module
from types import MappingProxyType
from typing import Callable, Iterable, Mapping

from dpost_v2.application.contracts.plugin_contracts import (
    PluginCapabilities,
    PluginContractError,
    validate_plugin_contract,
)


class PluginDiscoveryError(RuntimeError):
    """Base exception for plugin discovery failures."""


class PluginDiscoveryImportError(PluginDiscoveryError):
    """Raised when a plugin module cannot be imported."""

    def __init__(self, module_name: str, reason: str) -> None:
        self.module_name = module_name
        self.reason = reason
        super().__init__(f"failed to import plugin module {module_name!r}: {reason}")


class PluginDiscoveryManifestError(PluginDiscoveryError):
    """Raised when discovered module manifest/contracts are invalid."""

    def __init__(self, module_name: str, reason: str) -> None:
        self.module_name = module_name
        self.reason = reason
        super().__init__(f"invalid plugin manifest in {module_name!r}: {reason}")


class PluginDiscoveryDuplicateIdError(PluginDiscoveryError):
    """Raised when discovery finds duplicate plugin ids."""


class PluginDiscoveryFamilyError(PluginDiscoveryError):
    """Raised when a descriptor family is not allowed by discovery policy."""


@dataclass(frozen=True, slots=True)
class PluginDiscoveryIssue:
    """Structured discovery issue used in diagnostics payloads."""

    module_name: str
    reason: str


@dataclass(frozen=True, slots=True)
class PluginDescriptor:
    """Validated plugin descriptor used by catalog and host layers."""

    plugin_id: str
    family: str
    version: str
    contract_version: str
    supported_profiles: tuple[str, ...]
    capabilities: PluginCapabilities
    module_name: str
    module_exports: Mapping[str, object]

    def __post_init__(self) -> None:
        if not isinstance(self.plugin_id, str) or not self.plugin_id.strip():
            raise ValueError("plugin_id must be a non-empty string")
        if self.family not in {"device", "pc"}:
            raise ValueError("family must be 'device' or 'pc'")
        if not isinstance(self.version, str) or not self.version.strip():
            raise ValueError("version must be a non-empty string")
        if (
            not isinstance(self.contract_version, str)
            or not self.contract_version.strip()
        ):
            raise ValueError("contract_version must be a non-empty string")
        if not isinstance(self.module_name, str) or not self.module_name.strip():
            raise ValueError("module_name must be a non-empty string")
        if not isinstance(self.module_exports, Mapping):
            raise ValueError("module_exports must be a mapping")
        object.__setattr__(
            self, "module_exports", MappingProxyType(dict(self.module_exports))
        )

        normalized_profiles = tuple(
            profile.strip().lower()
            for profile in self.supported_profiles
            if isinstance(profile, str) and profile.strip()
        )
        object.__setattr__(self, "supported_profiles", normalized_profiles)


@dataclass(frozen=True, slots=True)
class PluginDiscoveryDiagnostics:
    """Discovery diagnostics for skipped/invalid plugin candidates."""

    import_errors: tuple[PluginDiscoveryIssue, ...] = ()
    manifest_errors: tuple[PluginDiscoveryIssue, ...] = ()
    skipped_modules: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PluginDiscoveryResult:
    """Output of plugin discovery including descriptors and diagnostics."""

    descriptors: tuple[PluginDescriptor, ...]
    diagnostics: PluginDiscoveryDiagnostics
    fingerprint: str


def discover_plugins(
    *,
    module_names: Iterable[str],
    module_importer: Callable[[str], object] | None = None,
    allowed_families: Iterable[str] = ("device", "pc"),
) -> PluginDiscoveryResult:
    """Discover plugin descriptors from modules without activating plugins."""
    importer = module_importer or import_module
    allowed = {
        family.strip().lower()
        for family in allowed_families
        if isinstance(family, str) and family.strip()
    }
    if not allowed:
        raise PluginDiscoveryFamilyError("allowed_families cannot be empty")

    descriptors: list[PluginDescriptor] = []
    import_issues: list[PluginDiscoveryIssue] = []
    manifest_issues: list[PluginDiscoveryIssue] = []
    skipped: list[str] = []
    seen_plugin_ids: set[str] = set()

    for module_name in sorted(set(module_names)):
        try:
            module = importer(module_name)
        except Exception as exc:  # noqa: BLE001
            import_issues.append(
                PluginDiscoveryIssue(module_name=module_name, reason=str(exc))
            )
            skipped.append(module_name)
            continue

        exports = _module_exports(module)
        try:
            metadata = validate_plugin_contract(exports)
            capabilities = _coerce_capabilities(exports["capabilities"]())
        except (PluginContractError, KeyError) as exc:
            manifest_issues.append(
                PluginDiscoveryIssue(module_name=module_name, reason=str(exc))
            )
            skipped.append(module_name)
            continue

        if metadata.family not in allowed:
            raise PluginDiscoveryFamilyError(
                f"plugin {metadata.plugin_id!r} declared family "
                f"{metadata.family!r} not allowed by policy"
            )
        if metadata.plugin_id in seen_plugin_ids:
            raise PluginDiscoveryDuplicateIdError(
                f"duplicate plugin id discovered: {metadata.plugin_id}"
            )
        seen_plugin_ids.add(metadata.plugin_id)

        descriptors.append(
            PluginDescriptor(
                plugin_id=metadata.plugin_id,
                family=metadata.family,
                version=metadata.version,
                contract_version=metadata.contract_version,
                supported_profiles=metadata.supported_profiles,
                capabilities=capabilities,
                module_name=module_name,
                module_exports=exports,
            )
        )

    descriptors_sorted = tuple(
        sorted(descriptors, key=lambda item: (item.plugin_id, item.module_name))
    )
    diagnostics = PluginDiscoveryDiagnostics(
        import_errors=tuple(import_issues),
        manifest_errors=tuple(manifest_issues),
        skipped_modules=tuple(sorted(set(skipped))),
        warnings=(),
    )
    return PluginDiscoveryResult(
        descriptors=descriptors_sorted,
        diagnostics=diagnostics,
        fingerprint=_discovery_fingerprint(descriptors_sorted),
    )


def discover_from_namespaces(
    *,
    namespace_families: Mapping[str, str] | None = None,
    module_importer: Callable[[str], object] | None = None,
    iter_modules_fn: Callable[[Iterable[str], str], Iterable[object]] | None = None,
    include_hidden_packages: bool = False,
) -> PluginDiscoveryResult:
    """Discover plugins from namespace packages using deterministic enumeration."""
    mapping = dict(
        namespace_families
        or {
            "dpost_v2.plugins.devices": "device",
            "dpost_v2.plugins.pcs": "pc",
        }
    )
    normalized_mapping: dict[str, str] = {}
    for namespace_name, family in mapping.items():
        if not isinstance(namespace_name, str) or not namespace_name.strip():
            raise PluginDiscoveryFamilyError(
                "namespace_families keys must be non-empty strings"
            )
        if not isinstance(family, str) or not family.strip():
            raise PluginDiscoveryFamilyError(
                f"namespace {namespace_name!r} family token must be a non-empty string"
            )
        normalized_family = family.strip().lower()
        if normalized_family not in {"device", "pc"}:
            raise PluginDiscoveryFamilyError(
                f"namespace {namespace_name!r} has unsupported family token {family!r}"
            )
        normalized_mapping[namespace_name] = normalized_family

    importer = module_importer or import_module
    iter_modules = iter_modules_fn or pkgutil.iter_modules

    module_names: list[str] = []
    module_expected_families: dict[str, str] = {}
    namespace_import_issues: list[PluginDiscoveryIssue] = []

    for namespace_name in sorted(normalized_mapping):
        try:
            namespace_module = importer(namespace_name)
        except Exception as exc:  # noqa: BLE001
            namespace_import_issues.append(
                PluginDiscoveryIssue(module_name=namespace_name, reason=str(exc))
            )
            continue

        namespace_path = getattr(namespace_module, "__path__", None)
        if not namespace_path:
            namespace_import_issues.append(
                PluginDiscoveryIssue(
                    module_name=namespace_name,
                    reason="namespace package has no __path__",
                )
            )
            continue

        for module_info in iter_modules(namespace_path, prefix=f"{namespace_name}."):
            if not getattr(module_info, "ispkg", False):
                continue
            package_name = str(getattr(module_info, "name"))
            leaf_name = package_name.rsplit(".", maxsplit=1)[-1]
            if not include_hidden_packages and leaf_name.startswith("_"):
                continue
            module_name = f"{package_name}.plugin"
            module_names.append(module_name)
            module_expected_families[module_name] = normalized_mapping[namespace_name]

    discovered = discover_plugins(
        module_names=tuple(sorted(set(module_names))),
        module_importer=importer,
        allowed_families=tuple(sorted(set(normalized_mapping.values()))),
    )

    for descriptor in discovered.descriptors:
        expected_family = module_expected_families.get(descriptor.module_name)
        if expected_family is None:
            continue
        if descriptor.family != expected_family:
            raise PluginDiscoveryFamilyError(
                f"plugin {descriptor.plugin_id!r} declared family "
                f"{descriptor.family!r} but namespace policy requires "
                f"{expected_family!r}"
            )

    if not namespace_import_issues:
        return discovered
    merged_diagnostics = PluginDiscoveryDiagnostics(
        import_errors=tuple(namespace_import_issues)
        + discovered.diagnostics.import_errors,
        manifest_errors=discovered.diagnostics.manifest_errors,
        skipped_modules=discovered.diagnostics.skipped_modules,
        warnings=discovered.diagnostics.warnings,
    )
    return PluginDiscoveryResult(
        descriptors=discovered.descriptors,
        diagnostics=merged_diagnostics,
        fingerprint=discovered.fingerprint,
    )


def _module_exports(module: object) -> Mapping[str, object]:
    if isinstance(module, Mapping):
        return dict(module)
    return dict(vars(module))


def _coerce_capabilities(value: object) -> PluginCapabilities:
    if isinstance(value, PluginCapabilities):
        return value
    if not isinstance(value, Mapping):
        raise PluginContractError(
            "capabilities() must return PluginCapabilities or mapping"
        )
    return PluginCapabilities(
        can_process=value.get("can_process"),  # type: ignore[arg-type]
        supports_preprocess=value.get("supports_preprocess"),  # type: ignore[arg-type]
        supports_batch=value.get("supports_batch"),  # type: ignore[arg-type]
        supports_sync=value.get("supports_sync"),  # type: ignore[arg-type]
    )


def _discovery_fingerprint(descriptors: Iterable[PluginDescriptor]) -> str:
    hasher = sha256()
    for descriptor in descriptors:
        profile_blob = ",".join(descriptor.supported_profiles)
        hasher.update(
            (
                f"{descriptor.plugin_id}|{descriptor.family}|{descriptor.version}|"
                f"{descriptor.contract_version}|{profile_blob}|{descriptor.module_name}"
            ).encode("utf-8")
        )
    return hasher.hexdigest()


__all__ = [
    "PluginDescriptor",
    "PluginDiscoveryDiagnostics",
    "PluginDiscoveryDuplicateIdError",
    "PluginDiscoveryError",
    "PluginDiscoveryFamilyError",
    "PluginDiscoveryImportError",
    "PluginDiscoveryIssue",
    "PluginDiscoveryManifestError",
    "PluginDiscoveryResult",
    "discover_from_namespaces",
    "discover_plugins",
]
