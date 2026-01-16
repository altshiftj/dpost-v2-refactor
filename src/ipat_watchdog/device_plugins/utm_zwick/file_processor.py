"""Processor for Zwick/Roell universal testing machine artefacts.

Supported workflow:
- Instrument produces iterative `.txt` (force/strain) snapshots (already numbered like `prefix-01.txt`)
  and rewrites the `.zs2` during a running series.
- Finalization happens when the `.csv` export appears (always last).
- We keep all `.txt` snapshots (sequence numbered) and move the latest `.zs2`.
- On session end or timeout, any incomplete series (no `.csv`) can optionally be flushed,
  promoting the *latest* `.txt` snapshot as the primary if configured.
"""
from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ipat_watchdog.core.config.schema import DeviceConfig
from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.core.processing.file_processor_abstract import (
    FileProbeResult,
    FileProcessorABS,
    PreprocessingResult,
    ProcessingOutput,
)
from ipat_watchdog.core.records.local_record import LocalRecord
from ipat_watchdog.core.storage.filesystem_utils import \
    get_unique_filename  # still used for txt snapshots
from ipat_watchdog.core.storage.filesystem_utils import move_item

logger = setup_logger(__name__)

# Helper: derive series key by stripping a trailing "-<digits>" from TXT stems
_TXT_COUNTER_RE = re.compile(r"^(?P<base>.+)-(?P<num>\d+)$")

def _series_key_for(stem: str, ext: str) -> str:
    if ext == ".txt":
        m = _TXT_COUNTER_RE.match(stem)
        if m:
            return m.group("base")
    return stem


@dataclass
class _SeriesState:
    sample: str
    last_zs2: Optional[Path] = None
    csv: Optional[Path] = None
    txt_snapshots: List[Path] = field(default_factory=list)
    txt_counter: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_update: datetime = field(default_factory=datetime.now)
    csv_received_at: Optional[datetime] = None


class FileProcessorUTMZwick(FileProcessorABS):
    """Handles UTM artefacts with support for series aggregation (zs2/txt/csv)."""

    def __init__(self, device_config: DeviceConfig) -> None:
        super().__init__(device_config)
        self.device_config = device_config
        # Houses per-sample series state until the exporter emits the final CSV.
        self._series: Dict[str, _SeriesState] = {}
        # Guard the series map because filesystem events race in from a background thread.
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Pre-processing
    # ------------------------------------------------------------------
    def device_specific_preprocessing(self, path: str) -> PreprocessingResult | None:
        """Stage incoming path (zs2/txt/csv) without moving files.

        - Track series state by *base* prefix (TXT stems are normalized by removing trailing -NN).
        - Return path if ready for processing (trigger on `.csv`).
        """
        p = Path(path)
        ext = p.suffix.lower()
        stem = p.stem
        key = _series_key_for(stem, ext)

        with self._lock:
            state = self._series.get(key)
            if not state:
                state = _SeriesState(sample=key)
                self._series[key] = state
                # Fresh series: start collecting artefacts until the CSV finalizer appears.
            state.last_update = datetime.now()

            if ext == ".zs2":
                state.last_zs2 = p
            elif ext == ".txt":
                state.txt_counter += 1
                state.txt_snapshots.append(p)
            elif ext == ".csv":
                state.csv = p
                state.csv_received_at = datetime.now()
            else:
                return None

            # Series finalize condition: csv present triggers processing immediately
            if state.csv:
                # Returning the CSV path signals the pipeline to process the entire staged series.
                return PreprocessingResult.passthrough(str(state.csv))

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
        - .txt files: iterative snapshots.
        - .csv files: final export.
        """
        path = Path(filepath)
        ext = path.suffix.lower()

        if ext == ".zs2":
            return FileProbeResult.match(confidence=0.7, reason="Zwick .zs2 raw file")
        if ext == ".txt":
            return FileProbeResult.match(confidence=0.8, reason="Zwick text snapshot")
        if ext == ".csv":
            return FileProbeResult.match(confidence=0.9, reason="Zwick CSV export")

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
        # For CSV trigger, the src_path stem is already the base key.
        raw_prefix = Path(src_path).stem
        record_dir = Path(record_path)

        # Series path
        with self._lock:
            state = self._series.pop(raw_prefix, None)
        if not state:
            raise KeyError(f"No staged series for '{raw_prefix}'")
        # From here we deterministically move the staged artefacts into the record directory.

        # NOTE: We intentionally avoid overwriting existing artefacts now.
        #       Each .zs2 and .csv file is stored with a unique, incremented name
        #       (same strategy already used for .txt snapshots) to prevent
        #       accidental data loss when instrument restarts or replays.

        # Move latest zs2 (raw) with unique filename if present
        if state.last_zs2 and state.last_zs2.exists():
            unique_zs2_path = Path(
                get_unique_filename(str(record_dir), file_id, state.last_zs2.suffix)
            )
            try:
                move_item(str(state.last_zs2), str(unique_zs2_path))
                logger.debug(
                    "Moved raw zs2 '%s' -> '%s' (unique, no overwrite)",
                    state.last_zs2,
                    unique_zs2_path,
                )
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(
                    "Failed moving zs2 '%s' to '%s': %s", state.last_zs2, unique_zs2_path, exc
                )

        # Move csv as primary exported data with unique filename (no overwrite)
        primary = state.csv
        if primary and primary.exists():
            results_prefix = f"{file_id}_results"
            unique_results_path = Path(
                get_unique_filename(str(record_dir), results_prefix, primary.suffix)
            )
            try:
                move_item(str(primary), str(unique_results_path))
                logger.debug(
                    "Moved results '%s' -> '%s' (unique, no overwrite)",
                    primary,
                    unique_results_path,
                )
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(
                    "Failed moving results '%s' to '%s': %s", primary, unique_results_path, exc
                )

        # Persist snapshots (.txt) into record root (unique/incremented)
        if state.txt_snapshots:
            # Sort by natural numeric index if present; fallback to name
            def _txt_order_key(p: Path) -> tuple[int, str]:
                m = _TXT_COUNTER_RE.match(p.stem)
                return (int(m.group("num")) if m else -1, p.name)

            ordered = sorted(state.txt_snapshots, key=_txt_order_key)
            for snap in ordered:
                if not snap.exists():
                    continue
                file_id_tests = f"{file_id}_tests"
                dest = Path(get_unique_filename(record_path, file_id_tests, snap.suffix))
                try:
                    move_item(str(snap), str(dest))
                except Exception as exc:
                    logger.warning("Failed moving snapshot '%s' to '%s': %s", snap, dest, exc)

        return ProcessingOutput(final_path=str(record_dir), datatype="csv")

    # ------------------------------------------------------------------
    # Session end / flushing
    # ------------------------------------------------------------------
    def flush_series(self) -> None:  # pragma: no cover - integration path
        """Flush incomplete series at session end if configured.

        Incomplete series (no csv) are processed by promoting the latest `.txt`
        snapshot as the primary. If no snapshots exist, the series is dropped.
        """
        if not self.device_config.batch.flush_on_session_end:
            return

        with self._lock:
            states = list(self._series.values())
            self._series.clear()
        # Work on a snapshot outside the lock to keep filesystem event handling snappy.

        for state in states:
            if state.csv:
                # Already complete; put back for normal processing path
                with self._lock:
                    self._series[state.sample] = state
                continue

            # Promote latest txt (if any) by fabricating a csv trigger
            if state.txt_snapshots:
                # Choose highest numeric index if available
                latest = max(
                    state.txt_snapshots,
                    key=lambda p: int(m.group("num")) if (m := _TXT_COUNTER_RE.match(p.stem)) else -1,
                )
                state.csv = latest
                with self._lock:
                    self._series[state.sample] = state
            # else: nothing to do (no primary artefact)

    # Public duck-typed hook used by FileProcessManager (optional)
    def flush_incomplete(self) -> list[ProcessingOutput]:  # pragma: no cover - integration path
        """Finalize any remaining series without waiting for a .csv.

        Returns a list of ProcessingOutput objects so the caller can treat them
        like normal processing completions. Series with neither csv nor txt snapshots are skipped.
        """
        outputs: list[ProcessingOutput] = []
        with self._lock:
            states = list(self._series.values())
            self._series.clear()

        for state in states:
            # Promote best available primary (csv else last/highest-index txt)
            if state.csv:
                primary = state.csv
            elif state.txt_snapshots:
                primary = max(
                    state.txt_snapshots,
                    key=lambda p: int(m.group("num")) if (m := _TXT_COUNTER_RE.match(p.stem)) else -1,
                )
                state.csv = primary
            else:
                primary = None

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
