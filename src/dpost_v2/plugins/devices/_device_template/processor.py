"""Template device processor implementing prepare/process contract hooks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from dpost_v2.application.contracts.context import ProcessingContext
from dpost_v2.application.contracts.plugin_contracts import ProcessorResult

from dpost_v2.plugins.devices._device_template.settings import DevicePluginSettings


class DeviceProcessorFormatError(ValueError):
    """Raised when template processor receives unsupported input shape."""


class DeviceProcessorValidationError(ValueError):
    """Raised when required prepared fields are missing or invalid."""


@dataclass(frozen=True, slots=True)
class TemplateDeviceProcessor:
    """Reference processor for template-based device plugin implementations."""

    settings: DevicePluginSettings

    def prepare(self, raw_input: Mapping[str, Any]) -> Mapping[str, Any]:
        """Normalize raw input into deterministic prepared payload."""
        if not isinstance(raw_input, Mapping):
            raise DeviceProcessorFormatError("raw_input must be a mapping")
        source_path = raw_input.get("source_path")
        if not isinstance(source_path, str) or not source_path.strip():
            raise DeviceProcessorValidationError("source_path is required")
        extension = source_path.rsplit(".", maxsplit=1)[-1].lower() if "." in source_path else ""
        normalized_extension = f".{extension}" if extension else ""
        if normalized_extension and normalized_extension not in self.settings.source_extensions:
            raise DeviceProcessorFormatError(
                f"unsupported extension {normalized_extension!r} for "
                f"{self.settings.plugin_id}"
            )
        return {
            "source_path": source_path.strip(),
            "extension": normalized_extension,
            "plugin_id": self.settings.plugin_id,
        }

    def can_process(self, candidate: Mapping[str, Any]) -> bool:
        """Return True when candidate source extension is allowed by settings."""
        source_path = str(candidate.get("source_path", ""))
        if "." not in source_path:
            return False
        extension = f".{source_path.rsplit('.', maxsplit=1)[-1].lower()}"
        return extension in self.settings.source_extensions

    def process(
        self,
        prepared_input: Mapping[str, Any],
        context: ProcessingContext,
    ) -> ProcessorResult:
        """Return deterministic processor result from prepared input payload."""
        _ = context
        source_path = prepared_input.get("source_path")
        if not isinstance(source_path, str) or not source_path.strip():
            raise DeviceProcessorValidationError("prepared source_path is required")
        return ProcessorResult(
            final_path=source_path.strip(),
            datatype=f"{self.settings.plugin_id}/template",
        )

