"""Processor for UTM Zwick artefacts under canonical dpost plugin namespace."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

from dpost.application.config import DeviceConfig
from dpost.application.processing.file_processor_abstract import (
    FileProbeResult,
    FileProcessorABS,
    PreprocessingResult,
    ProcessingOutput,
)
from dpost.application.records.local_record import LocalRecord
from dpost.infrastructure.logging import setup_logger
from dpost.infrastructure.storage.filesystem_utils import (
    get_record_path,
    get_unique_filename,
    move_item,
)

logger = setup_logger(__name__)


@dataclass
class _SeriesState:
    series_key: str
    sample: str
    last_zs2: Optional[Path] = None
    sentinel_xlsx: Optional[Path] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_update: datetime = field(default_factory=datetime.now)
    xlsx_received_at: Optional[datetime] = None


class FileProcessorUTMZwick(FileProcessorABS):
    """Handle UTM artefacts with pairing/flush behavior parity."""

    def __init__(self, device_config: DeviceConfig) -> None:
        super().__init__(device_config)
        self.device_config = device_config
        self._series: Dict[str, _SeriesState] = {}
        self._lock = threading.Lock()

    def device_specific_preprocessing(
        self, src_path: str
    ) -> PreprocessingResult | None:
        p = Path(src_path)
        ext = p.suffix.lower()
        if ext not in {".zs2", ".xlsx"}:
            return None

        stem = p.stem
        key = self._series_key(stem)

        with self._lock:
            ttl_ready = self._find_ttl_ready_locked()
            if ttl_ready is not None:
                return PreprocessingResult.passthrough(str(ttl_ready.last_zs2))

            state = self._series.get(key)
            if ext == ".xlsx" and (state is None or state.last_zs2 is None):
                return None
            if state is None:
                state = _SeriesState(series_key=key, sample=stem)
                self._series[key] = state
            state.last_update = datetime.now()

            if ext == ".zs2":
                state.last_zs2 = p
            else:
                state.sample = stem
                state.sentinel_xlsx = p
                state.xlsx_received_at = datetime.now()

            if state.sentinel_xlsx is not None:
                return PreprocessingResult.passthrough(str(state.sentinel_xlsx))
        return None

    def is_appendable(
        self,
        record: LocalRecord,
        filename_prefix: str,
        extension: str,
    ) -> bool:
        return True

    def probe_file(self, filepath: str) -> FileProbeResult:
        path = Path(filepath)
        ext = path.suffix.lower()
        if ext == ".zs2":
            return FileProbeResult.match(confidence=0.7, reason="Zwick .zs2 raw file")
        if ext == ".xlsx":
            sibling_zs2 = path.with_suffix(".zs2")
            if sibling_zs2.exists():
                return FileProbeResult.match(
                    confidence=0.9,
                    reason="Zwick XLSX export",
                )
            return FileProbeResult.mismatch("Zwick XLSX requires sibling .zs2")
        return FileProbeResult.mismatch("Not a supported UTM artefact")

    def device_specific_processing(
        self,
        src_path: str,
        record_path: str,
        file_id: str,
        extension: str,
    ) -> ProcessingOutput:
        raw_prefix = Path(src_path).stem
        record_dir = Path(record_path)
        state = self._pop_series_state(raw_prefix)
        if state is None:
            raise KeyError(f"No staged series for '{raw_prefix}'")

        self._move_staged_artifact(
            source=state.last_zs2,
            record_dir=record_dir,
            filename_prefix=file_id,
            success_label="raw zs2",
            failure_label="zs2",
        )
        self._move_staged_artifact(
            source=state.sentinel_xlsx,
            record_dir=record_dir,
            filename_prefix=file_id,
            success_label="results",
            failure_label="results",
        )

        datatype = "xlsx" if state.sentinel_xlsx else "zs2"
        return ProcessingOutput(final_path=str(record_dir), datatype=datatype)

    def flush_series(self) -> None:  # pragma: no cover
        if not self.device_config.batch.flush_on_session_end:
            return
        self.flush_incomplete()

    def flush_incomplete(self) -> list[ProcessingOutput]:  # pragma: no cover
        outputs: list[ProcessingOutput] = []
        ttl_seconds = getattr(
            getattr(self.device_config, "batch", None), "ttl_seconds", 1800
        )
        ttl_cutoff = datetime.now() - timedelta(seconds=ttl_seconds)
        with self._lock:
            states = list(self._series.values())
            self._series.clear()

        for state in states:
            if state.sentinel_xlsx is None and state.last_update > ttl_cutoff:
                with self._lock:
                    self._series[state.series_key] = state
                continue
            primary = state.sentinel_xlsx or state.last_zs2
            if primary is None:
                continue

            with self._lock:
                self._series[state.series_key] = state

            try:
                device_abbr = getattr(self.device_config.metadata, "device_abbr", None)
                record_dir = get_record_path(state.sample, device_abbr)
                output = self.device_specific_processing(
                    str(primary),
                    record_dir,
                    state.sample,
                    primary.suffix,
                )
                outputs.append(output)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Failed flushing incomplete series '%s': %s", state.sample, exc
                )
        return outputs

    def _find_ttl_ready_locked(self) -> _SeriesState | None:
        ttl_seconds = getattr(
            getattr(self.device_config, "batch", None), "ttl_seconds", 1800
        )
        ttl_cutoff = datetime.now() - timedelta(seconds=ttl_seconds)
        for state in self._series.values():
            if state.sentinel_xlsx is not None:
                continue
            if state.last_zs2 is None:
                continue
            if state.last_update <= ttl_cutoff:
                return state
        return None

    def _pop_series_state(self, raw_prefix: str) -> _SeriesState | None:
        series_key = self._series_key(raw_prefix)
        with self._lock:
            return self._series.pop(series_key, None)

    @staticmethod
    def _move_staged_artifact(
        source: Optional[Path],
        record_dir: Path,
        filename_prefix: str,
        success_label: str,
        failure_label: str,
    ) -> None:
        if source is None or not source.exists():
            return
        unique_path = Path(
            get_unique_filename(str(record_dir), filename_prefix, source.suffix)
        )
        try:
            move_item(str(source), str(unique_path))
            logger.debug(
                "Moved %s '%s' -> '%s' (unique, no overwrite)",
                success_label,
                source,
                unique_path,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Failed moving %s '%s' to '%s': %s",
                failure_label,
                source,
                unique_path,
                exc,
            )

    @staticmethod
    def _series_key(stem: str) -> str:
        return stem
