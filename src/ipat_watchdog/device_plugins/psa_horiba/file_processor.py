# ipat_watchdog/core/processing/file_processor_psa_horiba.py
from __future__ import annotations

from pathlib import Path
import time
import shutil
from typing import Dict, Optional

from ipat_watchdog.core.records.local_record import LocalRecord
from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS
from ipat_watchdog.core.storage.filesystem_utils import (
    move_item,
    move_to_exception_folder,
    get_unique_filename,
)
from ipat_watchdog.core.config.settings_store import SettingsStore
from ipat_watchdog.core.config import constants as _CONST
from ipat_watchdog.core.logging.logger import setup_logger

logger = setup_logger(__name__)


class FileProcessorPSAHoriba(FileProcessorABS):
    """
    Horiba Partica LA-960 processor.

    Emits per sample:
      <stem>.ngb    (raw)
      <stem>.csv    (results)

    Behavior:
      • First arrival becomes naming authority (primary_stem).
      • Second arrival is auto-renamed to primary_stem.<ext>.
      • When both exist, they’re staged to '<primary_stem>.__staged__'.
      • Processing zips .ngb and moves results into the record directory.
      • Both outputs share the **same counter**: e.g. '...-01.csv' and '...-01.ngb.zip'.
    """

    # in-memory buckets:  stem → {"t": float, "primary_stem": str, "first_kind": "raw"|"res",
    #                             "raw": Path|None, "res": Path|None, "res_ext": ".csv"|None}
    _TTL_SECONDS: int = 60 * 10  # orphan lifetime, 10 minutes

    def __init__(self):
        super().__init__()
        self._pending: Dict[str, Dict[str, object]] = {}

    # ---------- preprocessing --------------------------------------------------

    def device_specific_preprocessing(self, path: str) -> Optional[str]:
        p = Path(path)
        ext = p.suffix.lower()
        kind = self._classify(ext)  # "raw" | "res" | None

        if kind is None:
            # Unrelated filetype; let the manager handle it.
            return path

        stem = p.stem
        bucket = self._pending.get(stem)

        if bucket is None:
            bucket = {
                "t": time.time(),
                "primary_stem": stem,
                "first_kind": kind,
                "raw": None,
                "res": None,
                "res_ext": None,
            }
            self._pending[stem] = bucket

        # Fill the slot
        if kind == "raw":
            bucket["raw"] = p
        else:
            bucket["res"] = p
            bucket["res_ext"] = ext

        # Cross-stem pairing: attach a mismatched-stem second arrival
        if not self._is_complete(bucket):
            if bucket["first_kind"] == kind:
                target_key = self._find_open_bucket_missing(kind, exclude=stem)
                if target_key:
                    target = self._pending[target_key]
                    primary = str(target["primary_stem"])
                    desired = p.with_name(f"{primary}{ext}")
                    try:
                        if p != desired and not desired.exists():
                            p = p.rename(desired)
                            logger.debug("Auto-renamed '%s' → '%s'", path, desired)
                        if kind == "raw":
                            target["raw"] = p
                        else:
                            target["res"] = p
                            target["res_ext"] = ext
                        self._pending.pop(stem, None)
                        bucket = target
                        stem = target_key
                    except Exception as e:
                        logger.warning("Could not auto-rename/attach '%s' to '%s': %s", p, primary, e)

        self._purge_orphans()

        # Need both, and both must still exist
        if not self._is_complete(bucket) or not self._paths_exist(bucket):
            return None

        # Stage under the primary stem
        primary_stem = str(bucket["primary_stem"])
        stage_dir = self._unique_stage_dir(p.parent, primary_stem)
        stage_dir.mkdir(parents=True, exist_ok=True)

        raw_path: Path = bucket["raw"]  # type: ignore
        res_path: Path = bucket["res"]  # type: ignore

        for src in (raw_path, res_path):
            if src.exists():
                shutil.move(str(src), stage_dir / src.name)

        # Clear cache immediately
        self._pending.pop(stem, None)

        return str(stage_dir)

    # ---------- record-manager integration ------------------------------------

    def is_appendable(
        self, record: LocalRecord, filename_prefix: str, extension: str
    ) -> bool:
        return True

    # ---------- core processing ------------------------------------------------

    def device_specific_processing(
        self, src_path: str, record_path: str, filename_prefix: str, extension: str
    ) -> tuple[str, str]:
        """
        src_path is the staging folder created in preprocessing.
        """
        stage_dir = Path(src_path)
        record_dir = Path(record_path)

        # Find staged files (support .csv for results)
        ngb_list = list(stage_dir.glob("*.ngb"))
        csv_list = list(stage_dir.glob("*.csv"))

        if not ngb_list or not csv_list:
            raise FileNotFoundError(f"Staging folder missing required files: {stage_dir}")

        ngb_path = ngb_list[0]
        res_path = csv_list[0]
        res_ext = res_path.suffix.lower()  # ".csv"

        # Allocate ONE base stem with counter that's unique across BOTH outputs
        base_stem = self._allocate_base_stem(record_dir, filename_prefix, res_ext)

        # 1) ZIP the raw .ngb inside staging using that base stem, then remove the raw
        zip_stage = stage_dir / f"{base_stem}.ngb.zip"
        try:
            shutil.make_archive(
                base_name=str(zip_stage.with_suffix("")),  # drop ".zip" for make_archive
                format="zip",
                root_dir=str(ngb_path.parent),
                base_dir=ngb_path.name,
            )
            logger.debug("Archived '%s' → '%s'", ngb_path, zip_stage)
            ngb_path.unlink(missing_ok=True)
        except Exception as e:
            logger.error("Failed to archive '%s': %s", ngb_path, e)
            raise

        # 2) Move the results using the same base stem
        dest_res = record_dir / f"{base_stem}{res_ext}"
        try:
            move_item(str(res_path), str(dest_res))
        except Exception as e:
            logger.error("Failed to move '%s' to '%s': %s", res_path, dest_res, e)
            raise

        # 3) Move the ZIP into the record directory with the same base stem
        dest_zip = record_dir / f"{base_stem}.ngb.zip"
        try:
            move_item(str(zip_stage), str(dest_zip))
        except Exception as e:
            logger.error("Failed to move '%s' to '%s': %s", zip_stage, dest_zip, e)
            raise

        # 4) Best-effort: remove empty staging folder
        try:
            if not any(stage_dir.iterdir()):
                stage_dir.rmdir()
        except Exception:
            pass

        return str(record_dir), "psa"

    # ---------- helpers --------------------------------------------------------

    def _classify(self, ext: str) -> Optional[str]:
        if ext == ".ngb":
            return "raw"
        if ext == ".csv":
            return "res"
        return None

    def _is_complete(self, bucket: Dict[str, object]) -> bool:
        return bool(bucket.get("raw")) and bool(bucket.get("res"))

    def _paths_exist(self, bucket: Dict[str, object]) -> bool:
        raw = bucket.get("raw")
        res = bucket.get("res")
        return isinstance(raw, Path) and raw.exists() and isinstance(res, Path) and res.exists()

    def _find_open_bucket_missing(self, kind: str, exclude: str) -> Optional[str]:
        candidates = []
        for k, b in self._pending.items():
            if k == exclude:
                continue
            has_raw = bool(b.get("raw"))
            has_res = bool(b.get("res"))
            if kind == "raw" and not has_raw and has_res:
                candidates.append((k, b))
            if kind == "res" and not has_res and has_raw:
                candidates.append((k, b))
        if not candidates:
            return None
        candidates.sort(key=lambda kv: kv[1].get("t", 0), reverse=True)
        return candidates[0][0]

    def _purge_orphans(self):
        now = time.time()
        stale = [k for k, v in self._pending.items() if now - float(v.get("t", 0)) > self._TTL_SECONDS]
        for k in stale:
            entry = self._pending.pop(k, {})
            for label in ("raw", "res"):
                p = entry.get(label)
                if isinstance(p, Path) and p.exists():
                    try:
                        move_to_exception_folder(str(p))
                        logger.info("Purged orphan '%s'", p)
                    except Exception as e:
                        logger.warning("Could not purge orphan '%s': %s", p, e)

    def _unique_stage_dir(self, parent: Path, stem: str) -> Path:
        base = parent / f"{stem}.__staged__"
        if not base.exists():
            return base
        i = 2
        while True:
            candidate = parent / f"{stem}.__staged__{i}"
            if not candidate.exists():
                return candidate
            i += 1

    def _allocate_base_stem(self, record_dir: Path, filename_prefix: str, res_ext: str) -> str:
        """
        Pick one counter so BOTH outputs are unique:
        <base_stem>{res_ext}   and   <base_stem>.ngb.zip

        Strategy:
        1) Use get_unique_filename() for the results file to seed a counter.
        2) If the corresponding ZIP already exists, bump the counter until
            both names are free.
        """
        # 1) Seed from get_unique_filename for the results file
        seeded_path = Path(get_unique_filename(str(record_dir), filename_prefix, res_ext))
        base_stem = seeded_path.stem

        # Use the same separator the utility used
        try:
            sep = getattr(SettingsStore.get(), "ID_SEP", _CONST.ID_SEP)
        except Exception:
            sep = _CONST.ID_SEP

        # Parse the counter we just got (fallback to 1 if pattern unexpected)
        try:
            stem_no_cnt, cnt_str = base_stem.rsplit(sep, 1)
            counter = int(cnt_str) if stem_no_cnt == filename_prefix else 1
        except Exception:
            counter = 1

        # 2) Ensure the matching ZIP is also free; if not, bump until both are free
        while True:
            res_candidate = record_dir / f"{base_stem}{res_ext}"
            zip_candidate = record_dir / f"{base_stem}.ngb.zip"
            if not res_candidate.exists() and not zip_candidate.exists():
                return base_stem
            counter += 1
            base_stem = f"{filename_prefix}{sep}{counter:02d}"
