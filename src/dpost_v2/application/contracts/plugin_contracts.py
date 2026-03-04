"""Plugin capability and processor contracts for V2 application boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol, runtime_checkable

from dpost_v2.application.contracts.context import ProcessingContext, RuntimeContext


PLUGIN_CONTRACT_VERSION = "2.0.0"
_PLUGIN_CONTRACT_MAJOR = PLUGIN_CONTRACT_VERSION.split(".", maxsplit=1)[0]


class PluginContractError(ValueError):
    """Base exception for plugin contract validation failures."""


class DuplicatePluginRegistrationError(PluginContractError):
    """Raised when two plugins claim the same plugin id."""


class InvalidProcessorError(PluginContractError):
    """Raised when processor instance/result violates declared contract shape."""


@dataclass(frozen=True, slots=True)
class PluginCapabilities:
    """Explicit plugin capability flags used by host and factory selection."""

    can_process: bool
    supports_preprocess: bool
    supports_batch: bool
    supports_sync: bool

    def __post_init__(self) -> None:
        for field_name in (
            "can_process",
            "supports_preprocess",
            "supports_batch",
            "supports_sync",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise PluginContractError(f"{field_name} must be a bool")


@dataclass(frozen=True, slots=True)
class PluginMetadata:
    """Canonical plugin identity and compatibility metadata."""

    plugin_id: str
    family: str
    version: str
    contract_version: str
    supported_profiles: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.plugin_id, str) or not self.plugin_id.strip():
            raise PluginContractError("plugin_id must be a non-empty string")
        if self.family not in {"device", "pc"}:
            raise PluginContractError("family must be 'device' or 'pc'")
        if not isinstance(self.version, str) or not self.version.strip():
            raise PluginContractError("version must be a non-empty string")
        if not isinstance(self.contract_version, str) or not self.contract_version.strip():
            raise PluginContractError("contract_version must be a non-empty string")

        normalized_profiles: list[str] = []
        for profile in self.supported_profiles:
            if not isinstance(profile, str) or not profile.strip():
                raise PluginContractError("supported profile entries must be non-empty")
            normalized_profiles.append(profile.strip())
        object.__setattr__(self, "supported_profiles", tuple(normalized_profiles))


@dataclass(frozen=True, slots=True)
class ProcessorDescriptor:
    """Descriptor used to identify selected processor implementation details."""

    plugin_id: str
    processor_kind: str
    version: str

    def __post_init__(self) -> None:
        if not isinstance(self.plugin_id, str) or not self.plugin_id.strip():
            raise PluginContractError("processor descriptor plugin_id must be non-empty")
        if not isinstance(self.processor_kind, str) or not self.processor_kind.strip():
            raise PluginContractError(
                "processor descriptor processor_kind must be non-empty"
            )
        if not isinstance(self.version, str) or not self.version.strip():
            raise PluginContractError("processor descriptor version must be non-empty")


@dataclass(frozen=True, slots=True)
class ProcessorResult:
    """Normalized processor output consumed by ingestion runtime stages."""

    final_path: str
    datatype: str
    force_paths: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.final_path, str) or not self.final_path.strip():
            raise InvalidProcessorError("processor result final_path must be non-empty")
        if not isinstance(self.datatype, str) or not self.datatype.strip():
            raise InvalidProcessorError("processor result datatype must be non-empty")
        normalized_force_paths: list[str] = []
        for path in self.force_paths:
            if not isinstance(path, str) or not path.strip():
                raise InvalidProcessorError("force_paths entries must be non-empty")
            normalized_force_paths.append(path.strip())
        object.__setattr__(self, "force_paths", tuple(normalized_force_paths))


@runtime_checkable
class ProcessorContract(Protocol):
    """Processor interface contract consumed by ingestion processor factory."""

    def can_process(self, candidate: Mapping[str, Any]) -> bool:
        """Return True if processor can handle candidate payload."""

    def process(
        self,
        candidate: Mapping[str, Any],
        context: ProcessingContext,
    ) -> ProcessorResult | Mapping[str, Any]:
        """Transform candidate into normalized processor output."""


@runtime_checkable
class DevicePluginContract(Protocol):
    """Contract for device plugin modules exposed to host/discovery lanes."""

    def metadata(self) -> PluginMetadata | Mapping[str, Any]:
        """Return plugin identity metadata."""

    def capabilities(self) -> PluginCapabilities | Mapping[str, Any]:
        """Return explicit plugin capability flags."""

    def create_processor(self, settings: Mapping[str, Any]) -> ProcessorContract:
        """Build processor instance for ingestion runtime use."""

    def validate_settings(self, raw_settings: Mapping[str, Any]) -> Any:
        """Validate and normalize plugin settings."""


@runtime_checkable
class PcPluginContract(Protocol):
    """Contract for PC plugin modules exposed to host/discovery lanes."""

    def metadata(self) -> PluginMetadata | Mapping[str, Any]:
        """Return plugin identity metadata."""

    def capabilities(self) -> PluginCapabilities | Mapping[str, Any]:
        """Return explicit plugin capability flags."""

    def create_sync_adapter(self, settings: Mapping[str, Any]) -> object:
        """Build sync adapter for post-persist runtime paths."""

    def prepare_sync_payload(
        self,
        record: Mapping[str, Any],
        context: RuntimeContext,
    ) -> Mapping[str, Any]:
        """Prepare outbound sync payload."""


def _coerce_metadata(value: object) -> PluginMetadata:
    if isinstance(value, PluginMetadata):
        return value
    if not isinstance(value, Mapping):
        raise PluginContractError("metadata() must return PluginMetadata or mapping")
    supported_profiles = value.get("supported_profiles", ())
    if not isinstance(supported_profiles, tuple | list):
        raise PluginContractError("supported_profiles must be a sequence")
    return PluginMetadata(
        plugin_id=str(value.get("plugin_id", "")),
        family=str(value.get("family", "")),
        version=str(value.get("version", "")),
        contract_version=str(value.get("contract_version", "")),
        supported_profiles=tuple(supported_profiles),
    )


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


def _require_callable(module_exports: Mapping[str, object], export_name: str) -> None:
    export = module_exports.get(export_name)
    if not callable(export):
        raise PluginContractError(f"missing required plugin export: {export_name}")


def _validate_capability_combinations(
    metadata: PluginMetadata,
    capabilities: PluginCapabilities,
) -> None:
    if capabilities.supports_preprocess and not capabilities.can_process:
        raise PluginContractError(
            "supports_preprocess requires can_process=True capability"
        )
    if capabilities.supports_batch and not capabilities.can_process:
        raise PluginContractError("supports_batch requires can_process=True capability")

    if metadata.family == "device":
        if not capabilities.can_process:
            raise PluginContractError(
                "device plugins must declare can_process=True capability"
            )
    if metadata.family == "pc":
        if not capabilities.supports_sync:
            raise PluginContractError(
                "pc plugins must declare supports_sync=True capability"
            )


def is_contract_version_compatible(declared_version: str) -> bool:
    """Return True when declared version shares the current contract major version."""
    if not isinstance(declared_version, str) or "." not in declared_version:
        return False
    declared_major = declared_version.split(".", maxsplit=1)[0]
    return declared_major == _PLUGIN_CONTRACT_MAJOR


def validate_plugin_contract(
    module_exports: Mapping[str, object],
    *,
    seen_plugin_ids: set[str] | None = None,
) -> PluginMetadata:
    """Validate required plugin exports and metadata/capability shapes."""
    if not isinstance(module_exports, Mapping):
        raise PluginContractError("module_exports must be a mapping")

    _require_callable(module_exports, "metadata")
    _require_callable(module_exports, "capabilities")

    metadata_value = module_exports["metadata"]()
    capabilities_value = module_exports["capabilities"]()
    metadata = _coerce_metadata(metadata_value)
    capabilities = _coerce_capabilities(capabilities_value)

    if not is_contract_version_compatible(metadata.contract_version):
        raise PluginContractError(
            f"incompatible contract_version: {metadata.contract_version}"
        )

    _validate_capability_combinations(metadata, capabilities)

    if metadata.family == "device":
        _require_callable(module_exports, "create_processor")
        _require_callable(module_exports, "validate_settings")
        create_processor = module_exports.get("create_processor")
        if not callable(create_processor):
            raise PluginContractError("missing required plugin export: create_processor")
        try:
            processor_instance = create_processor({})
        except Exception as exc:  # pragma: no cover - defensive mapping
            raise InvalidProcessorError(
                "device create_processor failed during contract validation"
            ) from exc
        if not isinstance(processor_instance, ProcessorContract):
            raise InvalidProcessorError(
                "create_processor returned object that does not satisfy ProcessorContract"
            )
    else:
        _require_callable(module_exports, "create_sync_adapter")
        _require_callable(module_exports, "prepare_sync_payload")

    if capabilities.can_process and "create_processor" not in module_exports:
        raise PluginContractError("can_process=True requires create_processor export")

    if seen_plugin_ids is not None:
        if metadata.plugin_id in seen_plugin_ids:
            raise DuplicatePluginRegistrationError(
                f"duplicate plugin_id: {metadata.plugin_id}"
            )
        seen_plugin_ids.add(metadata.plugin_id)

    return metadata


def validate_processor_result(result: object) -> ProcessorResult:
    """Normalize and validate processor outputs for ingestion contract conformance."""
    if isinstance(result, ProcessorResult):
        return result
    if not isinstance(result, Mapping):
        raise InvalidProcessorError(
            "processor result must be ProcessorResult or mapping payload"
        )

    force_paths = result.get("force_paths", ())
    if isinstance(force_paths, list):
        force_paths = tuple(force_paths)
    if not isinstance(force_paths, tuple):
        raise InvalidProcessorError("force_paths must be tuple/list of strings")

    return ProcessorResult(
        final_path=str(result.get("final_path", "")),
        datatype=str(result.get("datatype", "")),
        force_paths=force_paths,  # type: ignore[arg-type]
    )


# Plugin-author facing aliases; this keeps names stable for external plugin code.
DevicePlugin = DevicePluginContract
PcPlugin = PcPluginContract
Processor = ProcessorContract
