# ipat_watchdog/core/processing/file_processor_psa_horiba.py
from __future__ import annotations

from pathlib import Path
import time
import shutil
from typing import Dict

from ipat_watchdog.core.records.local_record import LocalRecord
from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS
from ipat_watchdog.core.storage.filesystem_utils import (
    move_item,
    move_to_exception_folder,
    get_unique_filename,
)
from ipat_watchdog.core.logging.logger import setup_logger

logger = setup_logger(__name__)


class FileProcessorPSAHoriba(FileProcessorABS):
    """
    Processor for Horiba Partica LA-960 data.

    Emits per sample:
      <prefix>.ngb   (raw binary)
      <prefix>.csv   (post-processed results)

    Preprocessing:
      - Hold first arrival in memory until its twin appears.
      - When both EXIST, move them into a small staging folder and return that folder path.
        (The manager will route/rename on the folder so both artefacts travel together.)

    Processing:
      - Create the .ngb ZIP.
      - Move the .csv into the record directory with a unique filename.
      - Remove the raw .ngb and try to clean up the staging folder if empty.
    """

    # ──────────────────────────────────────────────────────────────────────────
    # staging buffer  (prefix  →  {"ngb": Path, "csv": Path, "t": float})
    # ──────────────────────────────────────────────────────────────────────────
    _TTL_SECONDS: int = 60 * 10  # orphan lifetime, 10 minutes

    def __init__(self):
        super().__init__()
        self._pending: Dict[str, Dict[str, Path | float]] = {}

    # ---------- preprocessing --------------------------------------------------

    def device_specific_preprocessing(self, path: str) -> str | None:
        p = Path(path)
        ext = p.suffix.lower().lstrip(".")
        if ext not in {"ngb", "csv"}:
            # Unrelated filetype for this device; let the manager handle it.
            return path

        prefix = p.stem
        bucket = self._pending.setdefault(prefix, {"t": time.time()})
        bucket[ext] = p
        self._purge_orphans()

        required = ("ngb", "csv")

        # Both keys present?
        if not all(k in bucket for k in required):
            return None

        # Ensure both paths STILL exist (they may have been moved to rename/exceptions)
        for k in required:
            v = bucket.get(k)
            if not (isinstance(v, Path) and v.exists()):
                bucket.pop(k, None)

        if not all(k in bucket for k in required):
            return None

        # Create a unique staging folder (avoid collisions if a stale one exists)
        stage_dir = self._unique_stage_dir(p.parent, prefix)
        stage_dir.mkdir(parents=True, exist_ok=True)

        # Move the two artefacts into the staging folder
        for k in required:
            src = bucket[k]
            shutil.move(str(src), stage_dir / src.name)

        # Clear cache NOW to avoid stale entries causing false "pair complete" later
        self._pending.pop(prefix, None)

        # Hand the folder to the manager so rename/exception moves both together
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

        # Find staged files inside the folder (do not rely on the cache)
        ngb_list = list(stage_dir.glob("*.ngb"))
        csv_list = list(stage_dir.glob("*.csv"))
        if not ngb_list or not csv_list:
            raise FileNotFoundError(f"Staging folder missing required files: {stage_dir}")

        ngb_path = ngb_list[0]
        csv_path = csv_list[0]

        # 1) Create the ZIP for the raw .ngb (in-place) then remove the raw
        #    Note: we build the archive from the file's parent (the stage folder)
        zip_stage = stage_dir / f"{filename_prefix}.ngb.zip"
        try:
            shutil.make_archive(
                base_name=str(zip_stage.with_suffix("")),  # drop .zip for make_archive
                format="zip",
                root_dir=str(ngb_path.parent),
                base_dir=ngb_path.name,
            )
            logger.debug("Archived '%s' → '%s'", ngb_path, zip_stage)
            ngb_path.unlink(missing_ok=True)
        except Exception as e:
            logger.error("Failed to archive '%s': %s", ngb_path, e)
            raise

        # 2) Move the .csv results into the record directory
        dest_csv = get_unique_filename(record_path, filename_prefix, ".csv")
        try:
            move_item(str(csv_path), dest_csv)
        except Exception as e:
            logger.error("Failed to move '%s' to '%s': %s", csv_path, dest_csv, e)
            raise

        # 3) Move the ZIP into the record directory
        #    (We expect this name to be unique because file_id is unique.)
        dest_zip = record_dir / f"{filename_prefix}.ngb.zip"
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

        # Tell the manager to register everything under the record directory
        return str(record_dir), "psa"

    # ---------- helpers --------------------------------------------------------

    def _purge_orphans(self):
        """Remove staged entries that never received their twin file within TTL."""
        now = time.time()
        stale = [k for k, v in self._pending.items() if now - v["t"] > self._TTL_SECONDS]
        for k in stale:
            entry = self._pending.pop(k, {})
            for ext, p in list(entry.items()):
                if isinstance(p, Path) and p.exists():
                    try:
                        move_to_exception_folder(str(p))
                        logger.info("Purged orphan '%s'", p)
                    except Exception as e:
                        logger.warning("Could not purge orphan '%s': %s", p, e)

    def _unique_stage_dir(self, parent: Path, prefix: str) -> Path:
        """Create a unique staging dir path like '<prefix>.__staged__' (with suffix if needed)."""
        base = parent / f"{prefix}.__staged__"
        if not base.exists():
            return base
        i = 2
        while True:
            candidate = parent / f"{prefix}.__staged__{i}"
            if not candidate.exists():
                return candidate
            i += 1
