"""Processor for Zwick/Roell universal testing machine artefacts.

Supported workflow:
- A `.zs2` raw file is staged by prefix `usr-inst-sample_name`.
- Finalization happens only when the sentinel `.xlsx` appears with the same prefix.
- If the sentinel never arrives, a TTL fallback can process the `.zs2` alone.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

from ipat_watchdog.core.config.schema import DeviceConfig
from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.core.processing.file_processor_abstract import (
    FileProbeResult,
    FileProcessorABS,
    PreprocessingResult,
    ProcessingOutput,
)
from ipat_watchdog.core.records.local_record import LocalRecord
from ipat_watchdog.core.storage.filesystem_utils import get_unique_filename
from ipat_watchdog.core.storage.filesystem_utils import move_item
from ipat_watchdog.core.storage.filesystem_utils import sanitize_and_validate

logger = setup_logger(__name__)

@dataclass
class _SeriesState:
    sample: str
    last_zs2: Optional[Path] = None
    sentinel_xlsx: Optional[Path] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_update: datetime = field(default_factory=datetime.now)
    xlsx_received_at: Optional[datetime] = None


class FileProcessorUTMZwick(FileProcessorABS):
    """Handles UTM artefacts with support for series aggregation (zs2/xlsx)."""

    def __init__(self, device_config: DeviceConfig) -> None:
        super().__init__(device_config)
        self.device_config = device_config
        # Houses per-sample series state until the exporter emits the sentinel XLSX.
        self._series: Dict[str, _SeriesState] = {}
        # Guard the series map because filesystem events race in from a background thread.
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Pre-processing
    # ------------------------------------------------------------------
    def device_specific_preprocessing(self, path: str) -> PreprocessingResult | None:
        """Stage incoming path (zs2/xlsx) without moving files.

        - Track series state by prefix from the filename stem.
        - Return path if ready for processing (trigger on sentinel `.xlsx`).
        """
        p = Path(path)
        ext = p.suffix.lower()
        if ext not in {".zs2", ".xlsx"}:
            return None

        stem = p.stem
        key, is_valid = self._normalize_series_key(stem)
        if not is_valid:
            logger.warning("Zwick: invalid prefix %r for %s", stem, p.name)
            return None

        with self._lock:
            ttl_ready = self._find_ttl_ready_locked()
            if ttl_ready is not None:
                return PreprocessingResult.passthrough(str(ttl_ready.last_zs2))

            state = self._series.get(key)
            if ext == ".xlsx" and (state is None or state.last_zs2 is None):
                return None

            if not state:
                state = _SeriesState(sample=key)
                self._series[key] = state
                # Fresh series: start collecting artefacts until the XLSX finalizer appears.
            state.last_update = datetime.now()

            if ext == ".zs2":
                state.last_zs2 = p
            elif ext == ".xlsx":
                state.sentinel_xlsx = p
                state.xlsx_received_at = datetime.now()

            # Series finalize condition: sentinel xlsx present triggers processing immediately
            if state.sentinel_xlsx:
                return PreprocessingResult.passthrough(str(state.sentinel_xlsx))

        return None

    def is_appendable(
        self,
        record: LocalRecord,
        filename_prefix: str,
        extension: str,
    ) -> bool:
        return True

    # ------------------------------------------------------------------
    # Probing
    # ------------------------------------------------------------------
    def probe_file(self, filepath: str) -> FileProbeResult:
        """Recognize UTM artefacts by extension.

        - .zs2 files: treat as likely match (binary proprietary).
        - .xlsx files: sentinel export.
        """
        path = Path(filepath)
        ext = path.suffix.lower()

        if ext == ".zs2":
            return FileProbeResult.match(confidence=0.7, reason="Zwick .zs2 raw file")
        if ext == ".xlsx":
            sibling_zs2 = path.with_suffix(".zs2")
            if sibling_zs2.exists():
                return FileProbeResult.match(confidence=0.9, reason="Zwick XLSX export")
            return FileProbeResult.mismatch("Zwick XLSX requires sibling .zs2")

        return FileProbeResult.mismatch("Not a supported UTM artefact")

    # ------------------------------------------------------------------
    # Core processing
    # ------------------------------------------------------------------
    def device_specific_processing(
        self,
        src_path: str,
        record_path: str,
        file_id: str,
        extension: str,
    ) -> ProcessingOutput:
        # For XLSX or TTL trigger, the src_path stem is already the base key.
        raw_prefix = Path(src_path).stem
        record_dir = Path(record_path)

        # Series path
        state = self._pop_series_state(raw_prefix)
        if not state:
            raise KeyError(f"No staged series for '{raw_prefix}'")
        # From here we deterministically move the staged artefacts into the record directory.

        # Move latest zs2 (raw) with unique filename if present
        self._move_staged_artifact(
            source=state.last_zs2,
            record_dir=record_dir,
            filename_prefix=file_id,
            success_label="raw zs2",
            failure_label="zs2",
        )

        # Move sentinel xlsx as primary exported data with unique filename (no overwrite)
        primary = state.sentinel_xlsx
        self._move_staged_artifact(
            source=primary,
            record_dir=record_dir,
            filename_prefix=f"{file_id}_results",
            success_label="results",
            failure_label="results",
        )

        datatype = "xlsx" if state.sentinel_xlsx else "zs2"
        return ProcessingOutput(final_path=str(record_dir), datatype=datatype)

    # ------------------------------------------------------------------
    # Session end / flushing
    # ------------------------------------------------------------------
    def flush_series(self) -> None:  # pragma: no cover - integration path
        """Flush incomplete series at session end if configured.

        Incomplete series (no sentinel xlsx) are retained for TTL-based flush.
        """
        if not self.device_config.batch.flush_on_session_end:
            return
        self.flush_incomplete()

    # Public duck-typed hook used by FileProcessManager (optional)
    def flush_incomplete(self) -> list[ProcessingOutput]:  # pragma: no cover - integration path
        """Finalize any remaining series without waiting for a sentinel `.xlsx`.

        Returns a list of ProcessingOutput objects so the caller can treat them
        like normal processing completions. Series without a `.zs2` are skipped.
        """
        outputs: list[ProcessingOutput] = []
        ttl_seconds = getattr(getattr(self.device_config, "batch", None), "ttl_seconds", 1800)
        ttl_cutoff = datetime.now() - timedelta(seconds=ttl_seconds)
        with self._lock:
            states = list(self._series.values())
            self._series.clear()

        for state in states:
            if state.sentinel_xlsx is None and state.last_update > ttl_cutoff:
                with self._lock:
                    self._series[state.sample] = state
                continue
            primary = state.sentinel_xlsx or state.last_zs2

            if not primary:
                continue

            # Put back state so processing path can pop it
            with self._lock:
                self._series[state.sample] = state

            try:
                out = self.device_specific_processing(
                    str(primary),
                    self._current_record_dir_fallback(primary),
                    state.sample,
                    primary.suffix,
                )
                outputs.append(out)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Failed flushing incomplete series '%s': %s", state.sample, exc)
        return outputs

    def _current_record_dir_fallback(self, primary: Path) -> str:
        """Best-effort: choose the parent directory of primary as record dir if no manager provided."""
        return str(primary.parent)

    def _find_ttl_ready_locked(self) -> _SeriesState | None:
        ttl_seconds = getattr(getattr(self.device_config, "batch", None), "ttl_seconds", 1800)
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
        """Return and remove staged state for the given filename stem."""
        series_key, _ = self._normalize_series_key(raw_prefix)
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
        """Move one staged artifact into record storage using unique naming."""
        if source is None or not source.exists():
            return

        unique_path = Path(get_unique_filename(str(record_dir), filename_prefix, source.suffix))
        try:
            move_item(str(source), str(unique_path))
            logger.debug(
                "Moved %s '%s' -> '%s' (unique, no overwrite)",
                success_label,
                source,
                unique_path,
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(
                "Failed moving %s '%s' to '%s': %s",
                failure_label,
                source,
                unique_path,
                exc,
            )

    @staticmethod
    def _normalize_series_key(stem: str) -> tuple[str, bool]:
        """Return a canonical series key and validity flag for a filename stem."""
        sanitized, is_valid = sanitize_and_validate(stem)
        if is_valid:
            return sanitized, True
        return stem, False
