"""Processor for Kinexus Pro+ rheometer native + export artefacts (Horiba-style)."""
from __future__ import annotations

from pathlib import Path
import shutil
import time
from typing import Dict, Optional

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


def _id_separator() -> str:
    try:
        return current().id_separator
    except RuntimeError:
        return _CONST.ID_SEP


class FileProcessorRHEKinexus(FileProcessorABS):
    """
    Pairs Kinexus native `.rdf` (raw) with exported `.csv` (results), following the
    same staging/bucketing approach as the Horiba PSA processor you showed.

    Behaviour:
      - Preprocessing waits until both halves exist (raw+res), then moves them
        into a private `.__staged__` dir for atomic processing.
      - Processing creates `<base>_native.zip` from the `.rdf` and appends the `.csv`
        into the final record directory.
    """

    def __init__(self, device_config: DeviceConfig) -> None:
        super().__init__(device_config)
        self._pending: Dict[str, Dict[str, object]] = {}
        self.device_config = device_config

    # ------------------------------------------------------------------
    # Pre-processing (pair + stage)
    # ------------------------------------------------------------------
    def device_specific_preprocessing(self, path: str) -> Optional[str]:
        element = Path(path)
        ext = element.suffix.lower()
        native_exts = self.device_config.files.native_extensions
        exported_exts = self.device_config.files.exported_extensions

        kind = None
        if ext in native_exts:
            kind = "raw"     # .rdf
        elif ext in exported_exts:
            kind = "res"     # .csv

        if kind is None:
            return path  # let orchestrator decide

        stem = element.stem
        bucket = self._pending.setdefault(
            stem,
            {
                "t": time.time(),
                "primary_stem": stem,
                "first_kind": kind,
                "raw": None,
                "res": None,
                "res_ext": None,
            },
        )

        if kind == "raw":
            bucket["raw"] = element
        else:
            bucket["res"] = element
            bucket["res_ext"] = ext

        if not self._is_complete(bucket):
            self._maybe_attach_cross_stem(bucket, kind, element)

        self._purge_orphans()

        if not self._is_complete(bucket) or not self._paths_exist(bucket):
            return None

        # Both halves found -> stage them together (atomic handoff)
        primary_stem = str(bucket["primary_stem"])
        stage_dir = self._unique_stage_dir(element.parent, primary_stem)
        stage_dir.mkdir(parents=True, exist_ok=True)

        for src in (bucket["raw"], bucket["res"]):
            src_p = Path(src)
            shutil.move(str(src_p), stage_dir / src_p.name)

        self._pending.pop(stem, None)
        return str(stage_dir)

    # ------------------------------------------------------------------
    # Probing (CSV content heuristics)
    # ------------------------------------------------------------------
    def probe_file(self, filepath: str) -> FileProbeResult:
        path = Path(filepath)
        ext = path.suffix.lower()
        native_exts = self.device_config.files.native_extensions
        exported_exts = self.device_config.files.exported_extensions

        if ext in native_exts:
            return FileProbeResult.unknown("Binary native file; probe skipped")

        if ext not in exported_exts:
            return FileProbeResult.mismatch("Unsupported extension for Kinexus")

        try:
            snippet = self._read_text_prefix(path)
        except Exception as exc:  # pragma: no cover
            logger.debug("Kinexus probe read failed '%s': %s", path, exc)
            return FileProbeResult.unknown(str(exc))

        text = snippet.lower()
        positives = ["kinexus", "rspace", "netzsch", "malvern", "viscosity", "g'", "g\""]
        negatives = ["dissolution", "zwick", "ut m", "la-960", "partica"]

        score = sum(1 for t in positives if t in text) - sum(1 for t in negatives if t in text)
        if score <= 0:
            return FileProbeResult.unknown("CSV content inconclusive for Kinexus")

        confidence = min(0.55 + 0.15 * score, 0.95)
        return FileProbeResult.match(confidence=confidence, reason=f"Found Kinexus markers (score={score})")

    def is_appendable(self, record: LocalRecord, filename_prefix: str, extension: str) -> bool:
        return True

    @classmethod
    def get_device_id(cls) -> str:
        return "rhe_kinexus"

    # ------------------------------------------------------------------
    # Core processing (zip .rdf; append .csv)
    # ------------------------------------------------------------------
    def device_specific_processing(
        self,
        src_path: str,
        record_path: str,
        filename_prefix: str,
        extension: str,
    ) -> ProcessingOutput:
        stage_dir = Path(src_path)
        record_dir = Path(record_path)

        raw_candidates = list(stage_dir.glob("*.rdf"))
        res_candidates = [c for c in stage_dir.iterdir() if c.suffix.lower() != ".rdf"]

        if not raw_candidates or not res_candidates:
            raise RuntimeError(f"Stage directory {stage_dir} missing expected files")

        raw_path = raw_candidates[0]
        res_path = res_candidates[0]
        res_ext = res_path.suffix.lower()

        base_stem = self._allocate_base_stem(record_dir, filename_prefix, res_ext)

        # Zip native .rdf -> <base>_native.zip (same style as Horiba .ngb.zip)
        zip_stage = stage_dir / f"{base_stem}.zip"
        try:
            shutil.make_archive(
                base_name=str(zip_stage.with_suffix("")),  # strip .zip for make_archive
                format="zip",
                root_dir=str(raw_path.parent),
                base_dir=raw_path.name,
            )
            logger.debug("Archived '%s' to '%s'", raw_path, zip_stage)
            raw_path.unlink(missing_ok=True)
        except Exception as exc:
            logger.error("Failed to archive '%s': %s", raw_path, exc)
            raise

        # Move export into record: <base>.csv
        dest_res = record_dir / f"{base_stem}{res_ext}"
        try:
            move_item(str(res_path), str(dest_res))
        except Exception as exc:
            logger.error("Failed to move '%s' to '%s': %s", res_path, dest_res, exc)
            raise

        # Move native archive into record
        dest_zip = record_dir / f"{base_stem}_native.zip"
        try:
            move_item(str(zip_stage), str(dest_zip))
        except Exception as exc:
            logger.error("Failed to move '%s' to '%s': %s", zip_stage, dest_zip, exc)
            raise

        # Clean stage dir
        try:
            if not any(stage_dir.iterdir()):
                stage_dir.rmdir()
        except Exception:  # pragma: no cover
            pass

        return ProcessingOutput(final_path=str(record_dir), datatype="rhe")

    # ------------------------------------------------------------------
    # Helpers (same style as Horiba)
    # ------------------------------------------------------------------
    @staticmethod
    def _read_text_prefix(path: Path, bytes_limit: int = 4096) -> str:
        raw = path.read_bytes()[:bytes_limit]
        for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
            try:
                return raw.decode(enc, errors="ignore")
            except Exception:
                continue
        return raw.decode(errors="ignore")

    @staticmethod
    def _is_complete(bucket: Dict[str, object]) -> bool:
        return bool(bucket.get("raw")) and bool(bucket.get("res"))

    @staticmethod
    def _paths_exist(bucket: Dict[str, object]) -> bool:
        raw = bucket.get("raw")
        res = bucket.get("res")
        return isinstance(raw, Path) and raw.exists() and isinstance(res, Path) and res.exists()

    def _maybe_attach_cross_stem(self, bucket: Dict[str, object], kind: str, candidate: Path) -> None:
        if bucket["first_kind"] != kind:
            return
        target_key = self._find_open_bucket_missing(kind, exclude=candidate.stem)
        if not target_key:
            return
        target = self._pending[target_key]
        primary = str(target["primary_stem"])
        desired = candidate.with_name(f"{primary}{candidate.suffix}")
        try:
            if candidate != desired and not desired.exists():
                original = candidate
                candidate = candidate.rename(desired)
                logger.debug("Auto-renamed '%s' to '%s'", original, candidate)
            if kind == "raw":
                target["raw"] = candidate
            else:
                target["res"] = candidate
                target["res_ext"] = candidate.suffix.lower()
            self._pending.pop(candidate.stem, None)
        except Exception as exc:
            logger.warning("Could not auto-attach '%s' to '%s': %s", candidate, primary, exc)

    def _find_open_bucket_missing(self, kind: str, exclude: str) -> Optional[str]:
        candidates = []
        for key, payload in self._pending.items():
            if key == exclude:
                continue
            has_raw = bool(payload.get("raw"))
            has_res = bool(payload.get("res"))
            if kind == "raw" and not has_raw and has_res:
                candidates.append((key, payload))
            elif kind == "res" and not has_res and has_raw:
                candidates.append((key, payload))
        if not candidates:
            return None
        candidates.sort(key=lambda kv: kv[1].get("t", 0), reverse=True)
        return candidates[0][0]

    def _purge_orphans(self) -> None:
        now = time.time()
        # Reuse TTL concept if present; default to 900s when absent
        ttl = getattr(self.device_config, "batch", None)
        ttl_seconds = getattr(ttl, "ttl_seconds", 900)
        stale = [k for k, p in self._pending.items() if now - float(p.get("t", 0)) > ttl_seconds]
        for key in stale:
            payload = self._pending.pop(key, {})
            for label in ("raw", "res"):
                path_obj = payload.get(label)
                if isinstance(path_obj, Path) and path_obj.exists():
                    try:
                        move_to_exception_folder(str(path_obj))
                        logger.info("Purged orphan '%s'", path_obj)
                    except Exception as exc:
                        logger.warning("Could not purge orphan '%s': %s", path_obj, exc)

    def _unique_stage_dir(self, parent: Path, stem: str) -> Path:
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
            zip_candidate = record_dir / f"{base_stem}_native.zip"
            if not res_candidate.exists() and not zip_candidate.exists():
                return base_stem
            counter += 1
            base_stem = f"{filename_prefix}{sep}{counter:02d}"
