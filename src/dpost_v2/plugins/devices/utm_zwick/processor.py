"""Concrete processor for V2 utm_zwick plugin."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any, Mapping

from dpost_v2.application.contracts.context import ProcessingContext
from dpost_v2.application.contracts.plugin_contracts import ProcessorResult
from dpost_v2.plugins.devices._device_template.processor import (
    DeviceProcessorFormatError,
    DeviceProcessorValidationError,
)
from dpost_v2.plugins.devices.utm_zwick.settings import DevicePluginSettings


@dataclass(slots=True)
class _SeriesState:
    """In-memory state for one staged Zwick series."""

    series_key: str
    last_zs2_path: str | None = None
    sentinel_xlsx_path: str | None = None


@dataclass(slots=True)
class DeviceProcessor:
    """Stateful staged processor for paired `.zs2` and `.xlsx` inputs."""

    settings: DevicePluginSettings
    _series: dict[str, _SeriesState] = field(
        default_factory=dict, init=False, repr=False
    )
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def prepare(self, raw_input: Mapping[str, Any]) -> Mapping[str, Any]:
        """Normalize input and stage series state until a matching XLSX arrives."""
        source_path, extension = self._normalize_source_path(raw_input)
        series_key = Path(source_path).stem
        ready_to_process = False

        with self._lock:
            state = self._series.get(series_key)
            if extension == ".zs2":
                if state is None:
                    state = _SeriesState(series_key=series_key)
                    self._series[series_key] = state
                state.last_zs2_path = source_path
            elif state is not None and state.last_zs2_path is not None:
                state.sentinel_xlsx_path = source_path
                ready_to_process = True

        return {
            "source_path": source_path,
            "extension": extension,
            "plugin_id": self.settings.plugin_id,
            "series_key": series_key,
            "ready_to_process": ready_to_process,
        }

    def can_process(self, candidate: Mapping[str, Any]) -> bool:
        """Only allow immediate processing for a prepared matching XLSX finalizer."""
        source_path, extension = self._normalize_source_path(candidate)
        if extension != ".xlsx":
            return False

        if "ready_to_process" in candidate:
            return bool(candidate.get("ready_to_process"))

        series_key = str(candidate.get("series_key", Path(source_path).stem))
        with self._lock:
            state = self._series.get(series_key)
            return (
                state is not None
                and state.last_zs2_path is not None
                and state.sentinel_xlsx_path == source_path
            )

    def process(
        self,
        prepared_input: Mapping[str, Any],
        context: ProcessingContext,
    ) -> ProcessorResult:
        """Finalize a staged series as XLSX plus paired raw artefact."""
        _ = context
        source_path, extension = self._normalize_source_path(prepared_input)
        if extension != ".xlsx":
            raise ValueError("utm_zwick staged series requires an xlsx finalizer")

        series_key = str(prepared_input.get("series_key", Path(source_path).stem))
        with self._lock:
            state = self._series.get(series_key)
            if (
                state is None
                or state.last_zs2_path is None
                or state.sentinel_xlsx_path != source_path
            ):
                raise ValueError(f"No staged zs2/xlsx pair for series '{series_key}'")
            self._series.pop(series_key, None)

        return ProcessorResult(
            final_path=source_path,
            datatype="xlsx",
            force_paths=(state.last_zs2_path, source_path),
        )

    def _normalize_source_path(self, candidate: Mapping[str, Any]) -> tuple[str, str]:
        """Validate source path payload and normalize extension tokens."""
        if not isinstance(candidate, Mapping):
            raise DeviceProcessorFormatError("raw_input must be a mapping")

        source_path = candidate.get("source_path")
        if not isinstance(source_path, str) or not source_path.strip():
            raise DeviceProcessorValidationError("source_path is required")

        normalized_source_path = source_path.strip()
        extension = Path(normalized_source_path).suffix.lower()
        if extension and extension not in self.settings.source_extensions:
            raise DeviceProcessorFormatError(
                f"unsupported extension {extension!r} for {self.settings.plugin_id}"
            )
        return normalized_source_path, extension
