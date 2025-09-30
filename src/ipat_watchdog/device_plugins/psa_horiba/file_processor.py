"""Processor for Horiba Partica LA-960 exports."""
from __future__ import annotations

from pathlib import Path
import shutil
import time
import re
from dataclasses import dataclass, field
from typing import Dict, Optional, List

from ipat_watchdog.core.config import constants as _CONST
from ipat_watchdog.core.config import current
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


# ------------------------------
# Misc helpers / constants
# ------------------------------

def _id_separator() -> str:
    """Shared ID separator from runtime config, with safe fallback."""
    try:
        return current().id_separator
    except RuntimeError:
        return _CONST.ID_SEP


# Horiba header keys (lowercased) used for session grouping and naming.
# - "Hintergrund ID" appears to be a stable per-run identifier on many Horiba exports.
# - "Probenname" (Sample Name) is what we want to use for the final filenames.
_PROBENAME_KEY = "probenname"
_SESSION_KEY = "hintergrund id"

# Read enough of the file to include the Horiba header block (before numeric table).
_MAX_PREFIX_BYTES = 200_000

# Allow a broad set of filesystem-safe characters for provisional naming.
_VALID_NAME_RE = re.compile(r"[A-Za-z0-9._\-+=@()\[\]{} ]+$")


@dataclass
class _SessionBucket:
    """
    Tracks one in-flight Horiba session.

    A session consists of:
      - zero or more CSVs (measurement stages)
      - exactly one .ngb (arrives after the final stage)
    We group CSVs by their 'Bezeichnung' if present; otherwise use a time-based fallback.
    """
    t: float                    # last activity time (for orphan purging)
    dir: Path                   # source folder (watch folder)
    session_key: Optional[str] = None
    probename: Optional[str] = None
    csvs: List[Path] = field(default_factory=list)
    raw: Optional[Path] = None  # the .ngb
    first_arrival_kind: Optional[str] = None  # "res" or "raw"


class FileProcessorPSAHoriba(FileProcessorABS):
    """Pairs `.ngb` raw files with one-or-more exported `.csv` results, finalizing on `.ngb`."""
    def __init__(self, device_config: DeviceConfig) -> None:
        super().__init__(device_config)
        # Pending sessions keyed as "<folder>::<session_key>" or "<folder>::__open__<epoch>"
        self._pending: Dict[str, _SessionBucket] = {}
        self.device_config = device_config

    # ------------------------------------------------------------------
    # Pre-processing (ingest & stage sessions)
    # ------------------------------------------------------------------
    def device_specific_preprocessing(self, path: str) -> Optional[str]:
        """
        Session logic:
          - On CSV arrival: parse header, attach to a bucket by 'Bezeichnung' (session key),
            store/refresh 'Probenname'. Return None (not complete).
          - On .ngb arrival: attach to the newest open bucket in this folder that has CSVs
            (or create a placeholder if none yet). If the bucket now has csvs + .ngb, we
            stage the set into a unique temp directory and return its path to the orchestrator.
        """
        element = Path(path)
        ext = element.suffix.lower()
        native_exts = self.device_config.files.native_extensions
        exported_exts = self.device_config.files.exported_extensions

        # Classify file kind: "raw" (.ngb) vs "res" (.csv). If unsupported, let orchestrator decide.
        kind = None
        if ext in native_exts:
            kind = "raw"
        elif ext in exported_exts:
            kind = "res"
        else:
            return path  # Let the orchestrator decide what to do with unrelated file types

        folder = element.parent

        # ---------------------------
        # CSV ARRIVAL
        # ---------------------------
        if kind == "res":
            meta = {}
            try:
                meta = self._parse_csv_metadata(element)
            except Exception as e:
                logger.warning("PSA: failed parsing CSV metadata '%s': %s", element, e)

            session_key = meta.get(_SESSION_KEY)
            probename = meta.get(_PROBENAME_KEY)

            # Create/obtain a session bucket keyed by folder + session_key (fallback to time-based key).
            bkey = self._make_bucket_key(folder, session_key, f"__open__{int(time.time())}")
            bucket = self._touch_bucket(bkey, folder, first_kind="res")
            bucket.session_key = bucket.session_key or session_key
            if probename:
                # Always keep the latest seen Probename (user might correct between stages).
                bucket.probename = probename.strip()
            bucket.csvs.append(element)
            bucket.t = time.time()

            self._purge_orphans()
            return None  # not complete; wait for .ngb

        # ---------------------------
        # .NGB ARRIVAL
        # ---------------------------
        if kind == "raw":
            # Try to attach to the newest open bucket in this folder that has CSVs but no raw yet.
            bkey = self._pick_open_bucket_for_raw(folder)
            if not bkey:
                # No CSVs seen yet: create a placeholder bucket; CSVs will attach later.
                bkey = self._make_bucket_key(folder, None, f"__open__{int(time.time())}")
            bucket = self._touch_bucket(bkey, folder, first_kind=bucket.first_arrival_kind or "raw")
            bucket.raw = element
            bucket.t = time.time()

            # If we now have both CSVs and .ngb, stage the session and return the temp dir.
            if not self._close_ready(bucket):
                self._purge_orphans()
                return None

            # Prefer human-friendly staging dir name using probename if available, else raw stem.
            primary_stem = (bucket.probename or element.stem or "psa_session").strip()
            stage_dir = self._unique_stage_dir(folder, primary_stem)
            stage_dir.mkdir(parents=True, exist_ok=True)

            # Move all session artifacts into the staging directory.
            for src in [*bucket.csvs, element]:
                try:
                    shutil.move(str(src), stage_dir / src.name)
                except Exception as exc:
                    logger.error("PSA: failed staging '%s' -> '%s': %s", src, stage_dir, exc)
                    raise

            # Close this session.
            self._pending.pop(bkey, None)
            self._purge_orphans()
            return str(stage_dir)

        # Unreachable: kind is either "res" or "raw".
        return None

    # ------------------------------------------------------------------
    # Probing (to route CSVs to this processor)
    # ------------------------------------------------------------------
    def probe_file(self, filepath: str) -> FileProbeResult:
        """Inspect CSV headers to confirm PSA origin.

        Heuristics:
        - For exported files, read a small prefix and look for device-specific
          signatures (e.g. "HORIBA", "Partica", "LA-960").
        - For native files, probing is inconclusive (binary container), return
          unknown to allow selector-based routing.
        """
        path = Path(filepath)
        ext = path.suffix.lower()
        native_exts = self.device_config.files.native_extensions
        exported_exts = self.device_config.files.exported_extensions

        if ext in native_exts:
            return FileProbeResult.unknown("Binary raw file; probe skipped")

        if ext not in exported_exts:
            return FileProbeResult.mismatch("Unsupported extension for PSA Horiba")

        # Read a small chunk defensively; avoid loading entire file
        try:
            snippet = self._read_text_prefix(path)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.debug("PSA probe failed to read '%s': %s", path, exc)
            return FileProbeResult.unknown(str(exc))

        text = snippet.lower()
        positive = ["horiba", "partica", "la-960", "psa", "diameter"]
        negatives = ["dissolution", "cumulative release"]

        score = 0
        for token in positive:
            if token in text:
                score += 1
        for token in negatives:
            if token in text:
                score -= 1

        if score <= 0:
            return FileProbeResult.unknown("CSV content inconclusive for PSA Horiba")

        # Map simple count to a confidence in [0.6, 0.95]
        confidence = min(0.55 + 0.15 * score, 0.95)
        return FileProbeResult.match(confidence=confidence, reason=f"Found PSA markers (score={score})")

    def is_appendable(
        self,
        record: LocalRecord,
        filename_prefix: str,
        extension: str,
    ) -> bool:
        # We always accept additional items for the same record (series of CSVs).
        return True

    @classmethod
    def get_device_id(cls) -> str:
        return "psa_horiba"

    # ------------------------------------------------------------------
    # Core processing (rename/move artifacts to record dir)
    # ------------------------------------------------------------------
    def device_specific_processing(
        self,
        src_path: str,
        record_path: str,
        filename_prefix: str,
        extension: str,
    ) -> ProcessingOutput:
        """
        At this point, src_path is the staging folder containing:
          - one .ngb file
          - one or more CSVs from the same run
        We:
          1) Parse the LAST CSV for 'Probenname' (Sample Name).
          2) Use that value as the base stem for all outputs (even if invalid—FPM may reject later).
          3) Zip the .ngb and move it to the record folder.
          4) Move all CSVs to the record folder, renaming with a shared base + index when needed.
        """
        stage_dir = Path(src_path)
        record_dir = Path(record_path)

        raw_candidates = list(stage_dir.glob("*.ngb"))
        csv_candidates = [c for c in stage_dir.iterdir() if c.is_file() and c.suffix.lower() != ".ngb"]

        if not raw_candidates or not csv_candidates:
            raise RuntimeError(f"Stage directory {stage_dir} missing expected files")

        raw_path = raw_candidates[0]

        # Parse the LAST (latest mtime) CSV for Probename. This matches "final measurement sets the name".
        last_csv = max(csv_candidates, key=lambda p: p.stat().st_mtime)
        try:
            meta = self._parse_csv_metadata(last_csv)
        except Exception as e:
            logger.warning("PSA: could not parse metadata from '%s': %s", last_csv, e)
            meta = {}

        probename = (meta.get(_PROBENAME_KEY) or "").strip()

        # Use Probename as base stem if present; otherwise fallback to the orchestrator-provided prefix.
        # IMPORTANT: We only sanitize enough to avoid immediate FS errors; your FileProcessManager may still reject it.
        base = probename if probename else filename_prefix
        if not self._validate_probename(base):
            base = re.sub(r"[^\w.\-+@()\[\]{} ]+", "_", base)[:240] or filename_prefix

        # Choose extension from the first CSV for uniqueness seeding.
        first_ext = csv_candidates[0].suffix.lower()
        base_stem = self._allocate_base_stem(record_dir, base, first_ext)

        # --- 1) Zip the .ngb into "<base_stem>.ngb.zip"
        zip_stage = stage_dir / f"{base_stem}.ngb.zip"
        try:
            shutil.make_archive(
                base_name=str(zip_stage.with_suffix("")),
                format="zip",
                root_dir=str(raw_path.parent),
                base_dir=raw_path.name,
            )
            logger.debug("Archived '%s' to '%s'", raw_path, zip_stage)
            raw_path.unlink(missing_ok=True)
        except Exception as exc:
            logger.error("PSA: failed to archive '%s': %s", raw_path, exc)
            raise

        # --- 2) Move CSVs, renaming all to the common base.
        # First CSV takes "<base_stem><ext>", subsequent ones get "<base>__NN<ext>" using the configured separator.
        sep = _id_separator()
        counter = 1
        for i, src in enumerate(sorted(csv_candidates, key=lambda p: p.name)):
            if i == 0:
                dest_name = f"{base_stem}{src.suffix.lower()}"
            else:
                counter += 1
                dest_name = f"{base}{sep}{counter:02d}{src.suffix.lower()}"
                # de-dup in case name already exists
                while (record_dir / dest_name).exists():
                    counter += 1
                    dest_name = f"{base}{sep}{counter:02d}{src.suffix.lower()}"
            try:
                move_item(str(src), str(record_dir / dest_name))
            except Exception as exc:
                logger.error("PSA: failed moving '%s' -> '%s': %s", src, dest_name, exc)
                raise

        # --- 3) Move zipped .ngb
        try:
            move_item(str(zip_stage), str(record_dir / f"{base_stem}.ngb.zip"))
        except Exception as exc:
            logger.error("PSA: failed moving '%s': %s", zip_stage, exc)
            raise

        # Best-effort cleanup for the empty staging dir.
        try:
            if not any(stage_dir.iterdir()):
                stage_dir.rmdir()
        except Exception:  # pragma: no cover
            pass

        return ProcessingOutput(final_path=str(record_dir), datatype="psa")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _read_text_prefix(path: Path, bytes_limit: int = 4096) -> str:
        """Return the first bytes_limit bytes decoded with fallback encodings."""
        raw = path.read_bytes()[:bytes_limit]
        for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
            try:
                return raw.decode(enc, errors="ignore")
            except Exception:  # pragma: no cover - try next
                continue
        return raw.decode(errors="ignore")

    def _parse_csv_metadata(self, p: Path) -> Dict[str, str]:
        """
        Parse a small prefix of a Horiba CSV where header lines are 'Key<TAB>Value'.
        Stop when we reach the numeric data table (e.g., line starting with 'X(' or similar).
        Returns keys lowercased.
        """
        text = self._read_text_prefix(p, bytes_limit=_MAX_PREFIX_BYTES).strip()
        meta: Dict[str, str] = {}
        for line in text.splitlines():
            ls = line.strip()
            if not ls:
                continue
            # Heuristic: data table typically starts with X(µm) or similar
            if ls.startswith("X(") or ls.startswith("X(µm)") or ls.lower().startswith("x("):
                break
            parts = re.split(r"\t+", ls)
            if len(parts) >= 2:
                k = parts[0].strip().lower()
                v = parts[1].strip()
                if k and v:
                    meta[k] = v
        return meta

    @staticmethod
    def _classify(ext: str) -> Optional[str]:
        if ext == ".ngb":
            return "raw"
        if ext == ".csv":
            return "res"
        return None

    @staticmethod
    def _validate_probename(name: Optional[str]) -> bool:
        """Only prevent immediate filesystem issues; allow FileProcessManager to enforce stricter policy."""
        if not name:
            return False
        return bool(_VALID_NAME_RE.fullmatch(name)) and len(name) <= 240

    def _make_bucket_key(self, folder: Path, session_key: Optional[str], fallback_suffix: str) -> str:
        """Create a stable pending key for a session within a folder."""
        if session_key:
            return f"{folder}::{session_key}"
        return f"{folder}::{fallback_suffix}"

    def _touch_bucket(self, key: str, folder: Path, first_kind: str) -> _SessionBucket:
        """Get or create a session bucket; also record which kind arrived first (res/raw)."""
        b = self._pending.get(key)
        if b is None:
            b = _SessionBucket(t=time.time(), dir=folder, first_arrival_kind=first_kind)
            self._pending[key] = b
        return b

    def _close_ready(self, b: _SessionBucket) -> bool:
        """We can stage when we have at least one CSV and the .ngb."""
        return bool(b.csvs) and b.raw is not None

    def _pick_open_bucket_for_raw(self, folder: Path) -> Optional[str]:
        """
        Select the newest bucket in this folder that:
          - has CSVs (so it’s a real session), and
          - has not yet received the .ngb.
        """
        candidates = [(k, v) for k, v in self._pending.items() if v.dir == folder and v.raw is None and v.csvs]
        if not candidates:
            return None
        candidates.sort(key=lambda kv: kv[1].t, reverse=True)
        return candidates[0][0]

    def _purge_orphans(self) -> None:
        """
        Move very old pending files to the exception folder.
        Uses device_config.batch.ttl_seconds to decide staleness.
        """
        now = time.time()
        # NOTE: requires DeviceConfig.batch.ttl_seconds to be set appropriately in config.
        ttl = getattr(self.device_config, "batch", None)
        ttl_seconds = getattr(ttl, "ttl_seconds", 600) if ttl else 600

        stale_keys = [key for key, payload in self._pending.items() if now - float(payload.t) > ttl_seconds]
        for key in stale_keys:
            payload = self._pending.pop(key, None)
            if not payload:
                continue
            # Move any orphaned artifacts aside, so the operator can inspect them.
            for path_obj in [*payload.csvs, payload.raw]:
                if isinstance(path_obj, Path) and path_obj and path_obj.exists():
                    try:
                        move_to_exception_folder(str(path_obj))
                        logger.info("PSA: purged orphan '%s'", path_obj)
                    except Exception as exc:  # pragma: no cover - defensive
                        logger.warning("PSA: could not purge orphan '%s': %s", path_obj, exc)

    def _unique_stage_dir(self, parent: Path, stem: str) -> Path:
        """
        Generate a unique staging directory name in the watch folder.
        Example: "<stem>.__staged__", "<stem>.__staged__2", ...
        """
        base = parent / f"{stem}.__staged__"
        if not base.exists():
            return base
        counter = 2
        while True:
            candidate = parent / f"{stem}.__staged__{counter}"
            if not candidate.exists():
                return candidate
            counter += 1

    def _allocate_base_stem(self, record_dir: Path, filename_prefix: str, res_ext: str) -> str:
        """
        Reserve a unique "<base_stem>" such that:
          - "<base_stem><res_ext>" does not exist
          - "<base_stem>.ngb.zip" does not exist
        We re-use the global filename allocator for the first candidate, then
        increment using the configured id separator if needed.
        """
        seeded_path = Path(get_unique_filename(str(record_dir), filename_prefix, res_ext))
        base_stem = seeded_path.stem

        sep = _id_separator()
        try:
            stem_no_counter, counter_str = base_stem.rsplit(sep, 1)
            counter = int(counter_str) if stem_no_counter == filename_prefix else 1
        except Exception:
            counter = 1

        while True:
            res_candidate = record_dir / f"{base_stem}{res_ext}"
            zip_candidate = record_dir / f"{base_stem}.ngb.zip"
            if not res_candidate.exists() and not zip_candidate.exists():
                return base_stem
            counter += 1
            base_stem = f"{filename_prefix}{sep}{counter:02d}"
