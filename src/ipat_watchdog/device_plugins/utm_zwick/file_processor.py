"""Processor for Zwick/Roell universal testing machine artefacts.

Extended to support multi-test series aggregation:

Workflow (new): instrument produces iterative `.txt` (force/strain) snapshots
and rewrites the `.zs2` during a running series. Finalization happens when the
`.csv` export appears (always last). We keep all `.txt` snapshots (sequence
numbered) and only retain the latest `.zs2`. On session end or timeout, any
incomplete series (no `.csv`) can be flushed if configured.

Legacy pair mode (`.zs2` + `.xlsx`) is preserved for existing tests and until
the new `.csv` pipeline fully replaces it. If a `.xlsx` appears AND no `.csv`
has been seen for that prefix, we finalize immediately using the legacy path.
"""
from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import shutil
import time
from typing import Dict, List, Optional
import threading

from ipat_watchdog.core.config.schema import DeviceConfig
from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.core.processing.file_processor_abstract import (
    FileProcessorABS,
    FileProbeResult,
    ProcessingOutput,
)
from ipat_watchdog.core.records.local_record import LocalRecord
from ipat_watchdog.core.storage.filesystem_utils import (
    get_unique_filename,
    move_item,
    move_to_exception_folder,
)

logger = setup_logger(__name__)

# Internal staging marker recognized & ignored by FileProcessManager regex
INTERNAL_STAGING_MARKER = ".__staged__"

def _series_snapshot_dir_name(sample: str) -> str:
    """Return folder name for txt snapshots that the pipeline will ignore.

    We leverage the internal staging marker so the watcher / routing logic
    skips these transient accumulation folders.
    Pattern contributes to regex: prefix + .__staged__ + (extension-like tail)
    """
    return f"{sample}{INTERNAL_STAGING_MARKER}series"


@dataclass
class _SeriesState:
    sample: str
    last_zs2: Optional[Path] = None
    csv: Optional[Path] = None
    xlsx: Optional[Path] = None  # legacy path
    txt_snapshots: List[Path] = field(default_factory=list)
    txt_counter: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_update: datetime = field(default_factory=datetime.now)
    csv_received_at: Optional[datetime] = None


class FileProcessorUTMZwick(FileProcessorABS):
    """Handles UTM artefacts with support for series aggregation.

    Internal buffers:
      - _pending_legacy: keeps simple pair (.zs2 + .xlsx) for backward tests
      - _series: richer state for multi-test (.txt*, .zs2, .csv)
    """

    def __init__(self, device_config: DeviceConfig) -> None:
        super().__init__(device_config)
        self._pending_legacy: Dict[str, Dict[str, Path | float]] = {}
        self._series: Dict[str, _SeriesState] = {}
        self._lock = threading.Lock()

        # Read extended settings (provided via DeviceConfig.extra in builder)
        extra = getattr(device_config, "extra", {}) or {}
        self.series_timeout_minutes = int(extra.get("series_timeout_minutes", 30))
        self.csv_finalize_delay_seconds = int(extra.get("csv_finalize_delay_seconds", 3))
        self.flush_incomplete_on_session_end = bool(extra.get("flush_incomplete_on_session_end", True))
        self.keep_all_intermediate_txt = bool(extra.get("keep_all_intermediate_txt", True))

    # ------------------------------------------------------------------
    # Pre-processing
    # ------------------------------------------------------------------
    def device_specific_preprocessing(self, path: str) -> str | None:
        """Stage incoming path.

        New logic:
          - Track series state in _series for .zs2/.txt/.csv
          - Still support legacy (.zs2 + .xlsx) immediate finalize path
          - Return path if ready for processing (legacy) or if .csv series ready
        """
        p = Path(path)
        prefix = p.stem
        ext = p.suffix.lower()

        with self._lock:
            state = self._series.get(prefix)
            if not state:
                state = _SeriesState(sample=prefix)
                self._series[prefix] = state
            state.last_update = datetime.now()

            if ext == ".zs2":
                state.last_zs2 = p
            elif ext == ".txt":
                state.txt_counter += 1
                # Hidden & ignored aggregation folder for successive txt snapshots
                snapshot_dir = p.parent / _series_snapshot_dir_name(prefix)
                snapshot_dir.mkdir(exist_ok=True)
                snap_name = f"{prefix}_{state.txt_counter:03d}.txt"
                target = snapshot_dir / snap_name
                try:
                    shutil.copy2(p, target)
                    state.txt_snapshots.append(target)
                except Exception as exc:  # pragma: no cover - defensive
                    logger.warning("Failed to snapshot txt '%s': %s", p, exc)
            elif ext == ".csv":
                state.csv = p
                state.csv_received_at = datetime.now()
            elif ext == ".xlsx":  # legacy path
                state.xlsx = p
            else:
                # Unknown extension → ignore
                return None

            # Legacy finalize condition: have zs2 + xlsx and no csv seen
            if state.xlsx and state.last_zs2 and not state.csv:
                # Mirror old behaviour using legacy pending map so processing
                # function can stay mostly unchanged for that case.
                bucket = self._pending_legacy.setdefault(prefix, {"t": time.time()})
                bucket[".zs2"] = state.last_zs2
                bucket[".xlsx"] = state.xlsx
                return path  # triggers processing with the latest arrived path

            # Series finalize condition: csv present AND stabilization delay elapsed
            if state.csv and state.csv_received_at:
                if (datetime.now() - state.csv_received_at).total_seconds() >= self.csv_finalize_delay_seconds:
                    # Provide csv path as trigger for processing
                    return str(state.csv)
                # else: wait for delay
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
        """Recognize UTM artefacts by extension and lightweight signature check.

        - .zs2 files: treat as likely match (binary proprietary), moderate confidence.
        - .xlsx files: check the PK zip header and minimal OOXML markers if available.
        """
        path = Path(filepath)
        ext = path.suffix.lower()

        if ext == ".zs2":
            return FileProbeResult.match(confidence=0.7, reason="Zwick .zs2 raw file")

        if ext != ".xlsx":
            return FileProbeResult.mismatch("Not a UTM artefact")

        try:
            head = path.read_bytes()[:8]
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("UTM probe failed to read '%s': %s", path, exc)
            return FileProbeResult.unknown(str(exc))

        # XLSX should start with PK (zip). If not, it's not an OOXML workbook.
        if not head.startswith(b"PK"):
            return FileProbeResult.mismatch(".xlsx without PK header")

        return FileProbeResult.match(confidence=0.6, reason="XLSX workbook with ZIP header")

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
        raw_prefix = Path(src_path).stem
        record_dir = Path(record_path)

        # Determine if this is legacy pair or new series finalization
        bucket_legacy = self._pending_legacy.pop(raw_prefix, None)
        if bucket_legacy:
            zs2_path = Path(bucket_legacy[".zs2"])
            xlsx_path = Path(bucket_legacy[".xlsx"])
            return self._process_legacy_pair(zs2_path, xlsx_path, record_dir, file_id)

        # Series path
        with self._lock:
            state = self._series.pop(raw_prefix, None)
        if not state:
            raise KeyError(f"No staged series for '{raw_prefix}'")

        # Build archive of latest zs2 if present
        if state.last_zs2 and state.last_zs2.exists():
            zip_dest = record_dir / f"{file_id}.zs2.zip"
            try:
                shutil.make_archive(
                    base_name=str(zip_dest.with_suffix("")),
                    format="zip",
                    root_dir=str(state.last_zs2.parent),
                    base_dir=state.last_zs2.name,
                )
                logger.debug("Archived '%s' to '%s'", state.last_zs2, zip_dest)
                state.last_zs2.unlink(missing_ok=True)
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("Failed to archive '%s': %s", state.last_zs2, exc)
                raise

        # Move csv (preferred) else legacy xlsx as primary exported data
        primary = state.csv or state.xlsx
        datatype = "csv" if state.csv else "xlsx"
        if primary and primary.exists():
            destination_primary = get_unique_filename(record_path, file_id, primary.suffix)
            try:
                move_item(primary, destination_primary)
            except Exception as exc:
                logger.error("Failed to move '%s' to '%s': %s", primary, destination_primary, exc)
                raise

        # Persist snapshots (.txt) into a subfolder inside record for traceability
        if state.txt_snapshots:
            series_folder = record_dir / _series_snapshot_dir_name(file_id)
            series_folder.mkdir(exist_ok=True)
            for snap in state.txt_snapshots:
                if snap.exists():
                    dest = series_folder / snap.name
                    try:
                        if dest.exists():  # avoid overwrite
                            dest = series_folder / f"{snap.stem}_{int(time.time())}.txt"
                        shutil.move(str(snap), str(dest))
                    except Exception as exc:  # pragma: no cover - defensive
                        logger.warning("Failed moving snapshot '%s': %s", snap, exc)

        return ProcessingOutput(final_path=str(record_dir), datatype=datatype)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _process_legacy_pair(self, zs2_path: Path, xlsx_path: Path, record_dir: Path, file_id: str) -> ProcessingOutput:
        zip_dest = record_dir / f"{file_id}.zs2.zip"
        try:
            shutil.make_archive(
                base_name=str(zip_dest.with_suffix("")),
                format="zip",
                root_dir=str(zs2_path.parent),
                base_dir=zs2_path.name,
            )
            logger.debug("Archived '%s' to '%s' (legacy)", zs2_path, zip_dest)
            zs2_path.unlink(missing_ok=True)
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to archive '%s': %s", zs2_path, exc)
            raise

        destination_xlsx = get_unique_filename(str(record_dir), file_id, ".xlsx")
        try:
            move_item(xlsx_path, destination_xlsx)
        except Exception as exc:
            logger.error("Failed to move '%s' to '%s': %s", xlsx_path, destination_xlsx, exc)
            raise
        return ProcessingOutput(final_path=str(record_dir), datatype="xlsx")

    def _purge_orphans(self) -> None:
        """Purge orphaned legacy pairs only (series handled via timeout elsewhere)."""
        now = time.time()
        expired_keys = [key for key, payload in self._pending_legacy.items() if now - payload["t"] > self.device_config.batch.ttl_seconds]
        for key in expired_keys:
            payload = self._pending_legacy.pop(key, {})
            for candidate in payload.values():
                if isinstance(candidate, Path) and candidate.exists():
                    try:
                        move_to_exception_folder(candidate)
                        logger.info("Purged orphan legacy '%s'", candidate)
                    except Exception as exc:  # pragma: no cover - defensive
                        logger.warning("Could not purge orphan '%s': %s", candidate, exc)

    # ------------------------------------------------------------------
    # Backwards compatibility for tests referencing _pending
    # ------------------------------------------------------------------
    @property
    def _pending(self) -> Dict[str, Dict[str, Path | float]]:  # pragma: no cover - simple accessor
        return self._pending_legacy

    @_pending.setter  # pragma: no cover
    def _pending(self, value: Dict[str, Dict[str, Path | float]]):
        self._pending_legacy = value

    # Session end hook (if invoked externally)
    def flush_series(self) -> None:  # pragma: no cover - integration path
        """Flush incomplete series at session end if configured.

        Incomplete series (no csv) are processed treating latest available
        primary artefact (.xlsx if present else last .txt) similar to finalization.
        """
        if not self.flush_incomplete_on_session_end:
            return
        with self._lock:
            states = list(self._series.values())
            self._series.clear()
        for state in states:
            # Reinsert as legacy pair if conditions match, otherwise treat as series
            primary = state.csv or state.xlsx
            if primary and state.last_zs2 and not state.csv and state.xlsx:
                self._pending_legacy[state.sample] = {".zs2": state.last_zs2, ".xlsx": state.xlsx, "t": time.time()}
            else:
                # fabricate csv trigger to reuse processing path
                if state.csv is None:
                    state.csv = state.xlsx or (state.txt_snapshots[-1] if state.txt_snapshots else None)
                if state.csv:
                    self._series[state.sample] = state

    # Public duck-typed hook used by FileProcessManager (optional)
    def flush_incomplete(self) -> list[ProcessingOutput]:  # pragma: no cover - integration path
        """Finalize any remaining series without waiting for a .csv.

        Returns a list of ProcessingOutput objects so the caller can treat them
        like normal processing completions. Series with neither csv/xlsx nor
        txt snapshots are skipped.
        """
        outputs: list[ProcessingOutput] = []
        with self._lock:
            states = list(self._series.values())
            self._series.clear()
        for state in states:
            # Promote best available primary
            primary = state.csv or state.xlsx or (state.txt_snapshots[-1] if state.txt_snapshots else None)
            if not primary:
                continue
            # Reuse processing logic by re-inserting and calling device_specific_processing
            # Craft a synthetic trigger path extension
            ext = primary.suffix
            # Put back state so processing path can pop it
            with self._lock:
                self._series[state.sample] = state
            try:
                out = self.device_specific_processing(str(primary), self._current_record_dir_fallback(primary), state.sample, ext)
                outputs.append(out)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Failed flushing incomplete series '%s': %s", state.sample, exc)
        return outputs

    def _current_record_dir_fallback(self, primary: Path) -> str:
        """Best-effort: choose the parent directory of primary as record dir if no manager provided.

        Real integration should invoke flush before teardown, supplying an actual
        record directory. This fallback keeps method safe in isolation/testing.
        """
        return str(primary.parent)
