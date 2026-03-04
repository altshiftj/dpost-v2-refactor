"""Plugin-facing V2 contract aliases and compatibility helpers."""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from dpost_v2.application.contracts import context as context_contracts
from dpost_v2.application.contracts import events as events_contracts
from dpost_v2.application.contracts import plugin_contracts


class PluginContractsImportError(ImportError):
    """Raised when canonical contract symbols cannot be imported."""


class PluginContractVersionError(ValueError):
    """Raised when plugin declares an incompatible contract version."""


class PluginContractAliasConflictError(ValueError):
    """Raised when deprecated aliases conflict with canonical exports."""


class PluginContractMetadataError(ValueError):
    """Raised when compatibility metadata shape is invalid."""


PLUGIN_CONTRACT_VERSION = plugin_contracts.PLUGIN_CONTRACT_VERSION

_CANONICAL_ALIASES: dict[str, object] = {
    "RuntimeContext": context_contracts.RuntimeContext,
    "ProcessingContext": context_contracts.ProcessingContext,
    "BaseEvent": events_contracts.BaseEvent,
    "DevicePlugin": plugin_contracts.DevicePluginContract,
    "PcPlugin": plugin_contracts.PcPluginContract,
    "Processor": plugin_contracts.ProcessorContract,
    "PluginCapabilities": plugin_contracts.PluginCapabilities,
    "PluginMetadata": plugin_contracts.PluginMetadata,
    "ProcessorResult": plugin_contracts.ProcessorResult,
}
_DEPRECATED_ALIASES: dict[str, str] = {}


def _validate_alias_table() -> None:
    """Validate alias table consistency during module import."""
    canonical = set(_CANONICAL_ALIASES)
    deprecated = set(_DEPRECATED_ALIASES)
    overlaps = canonical & deprecated
    if overlaps:
        joined = ", ".join(sorted(overlaps))
        raise PluginContractAliasConflictError(
            f"deprecated aliases shadow canonical names: {joined}"
        )

    unknown_targets = {
        target
        for target in _DEPRECATED_ALIASES.values()
        if target not in _CANONICAL_ALIASES
    }
    if unknown_targets:
        joined = ", ".join(sorted(unknown_targets))
        raise PluginContractMetadataError(
            f"deprecated aliases reference unknown canonical names: {joined}"
        )


def is_contract_version_compatible(declared_version: str) -> bool:
    """Return True when plugin contract version is compatible with host major."""
    return plugin_contracts.is_contract_version_compatible(declared_version)


def require_contract_version_compatible(declared_version: object) -> str:
    """Validate and return a normalized compatible contract version."""
    if not isinstance(declared_version, str) or not declared_version.strip():
        raise PluginContractMetadataError(
            "declared contract_version must be a non-empty string"
        )
    normalized = declared_version.strip()
    if not is_contract_version_compatible(normalized):
        raise PluginContractVersionError(
            f"incompatible plugin contract version: {normalized}"
        )
    return normalized


def compatibility_metadata() -> Mapping[str, object]:
    """Return immutable metadata used by discovery/host compatibility gates."""
    return MappingProxyType(
        {
            "contract_version": PLUGIN_CONTRACT_VERSION,
            "canonical_aliases": tuple(sorted(_CANONICAL_ALIASES)),
            "deprecated_aliases": MappingProxyType(dict(_DEPRECATED_ALIASES)),
        }
    )


_validate_alias_table()

# Canonical plugin-facing aliases.
RuntimeContext = context_contracts.RuntimeContext
ProcessingContext = context_contracts.ProcessingContext
BaseEvent = events_contracts.BaseEvent
DevicePlugin = plugin_contracts.DevicePluginContract
PcPlugin = plugin_contracts.PcPluginContract
Processor = plugin_contracts.ProcessorContract
PluginCapabilities = plugin_contracts.PluginCapabilities
PluginMetadata = plugin_contracts.PluginMetadata
ProcessorResult = plugin_contracts.ProcessorResult
PluginContractError = plugin_contracts.PluginContractError
InvalidProcessorError = plugin_contracts.InvalidProcessorError
validate_plugin_contract = plugin_contracts.validate_plugin_contract
validate_processor_result = plugin_contracts.validate_processor_result


__all__ = [
    "BaseEvent",
    "DevicePlugin",
    "InvalidProcessorError",
    "PLUGIN_CONTRACT_VERSION",
    "PluginCapabilities",
    "PluginContractAliasConflictError",
    "PluginContractError",
    "PluginContractMetadataError",
    "PluginContractVersionError",
    "PluginContractsImportError",
    "PluginMetadata",
    "ProcessingContext",
    "Processor",
    "ProcessorResult",
    "RuntimeContext",
    "PcPlugin",
    "compatibility_metadata",
    "is_contract_version_compatible",
    "require_contract_version_compatible",
    "validate_plugin_contract",
    "validate_processor_result",
]
