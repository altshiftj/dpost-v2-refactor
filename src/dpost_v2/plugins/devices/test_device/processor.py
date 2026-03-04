"""Concrete processor for V2 test-device plugin."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from dpost_v2.application.contracts.context import ProcessingContext
from dpost_v2.application.contracts.plugin_contracts import ProcessorResult
from dpost_v2.plugins.devices.test_device.settings import DevicePluginSettings


@dataclass(frozen=True, slots=True)
class TestDeviceProcessor:
    """Deterministic test-device processor used by plugin host integration tests."""

    settings: DevicePluginSettings

    def prepare(self, raw_input: Mapping[str, Any]) -> Mapping[str, Any]:
        """Normalize raw input to prepared payload."""
        source_path = str(raw_input.get("source_path", "")).strip()
        if not source_path:
            raise ValueError("source_path is required")
        return {"source_path": source_path}

    def can_process(self, candidate: Mapping[str, Any]) -> bool:
        """Return True when source path extension is supported."""
        source_path = str(candidate.get("source_path", ""))
        if "." not in source_path:
            return False
        extension = f".{source_path.rsplit('.', maxsplit=1)[-1].lower()}"
        return extension in self.settings.source_extensions

    def process(
        self,
        candidate: Mapping[str, Any],
        context: ProcessingContext,
    ) -> ProcessorResult:
        """Return deterministic processor result for test-device plugin."""
        _ = context
        source_path = str(candidate.get("source_path", "")).strip()
        if not source_path:
            raise ValueError("source_path is required")
        return ProcessorResult(
            final_path=source_path,
            datatype="test_device/csv",
        )
