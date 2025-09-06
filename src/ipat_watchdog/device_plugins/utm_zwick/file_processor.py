# ipat_watchdog/core/processing/file_processor_zwick_utm.py
from __future__ import annotations

from pathlib import Path
import zipfile
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


class FileProcessorZwickUTM(FileProcessorABS):
    """
    Processor for Zwick/Roell universal-testing-machine data.

    Workflow
    --------
    1.  The UTM writes two files per sample, asynchronously:
            <prefix>.zs2   (raw binary)
            <prefix>.xlsx  (post-processed results)

    2.  `device_specific_preprocessing` stages the first arrival in RAM
        and returns **None** so FileProcessManager exits early (→ no UI yet).

    3.  When the twin file appears, the method returns the real path,
        the normal rename dialog runs exactly **once**, and
        `device_specific_processing` moves/renames **both** artefacts:

        - `<file_id>.xlsx` is copied to the record directory.
        - `<file_id>.zs2` is compressed to `<file_id>.zs2.zip`
          (about 16 % smaller on average).
        - the original `.zs2` is deleted after successful archiving.
    """

    # ──────────────────────────────────────────────────────────────────────────
    # staging buffer  (prefix  →  {"zs2": Path, "xlsx": Path, "t": float})
    # ──────────────────────────────────────────────────────────────────────────
    _TTL_SECONDS: int = 60 * 10          # orphan lifetime, 10 minutes

    def __init__(self):
        super().__init__()
        self._pending: Dict[str, Dict[str, Path | float]] = {}

    # ---------- preprocessing --------------------------------------------------

    def device_specific_preprocessing(self, path: str) -> str | None:
        """
        Hold the first file of a pair in memory until its counterpart appears.
        Returning *None* tells FileProcessManager to skip the rest of the flow.
        """
        p = Path(path)
        prefix = p.stem           # filenames are simple <prefix>.<ext>
        ext = p.suffix.lower().lstrip(".")

        bucket = self._pending.setdefault(prefix, {"t": time.time()})
        bucket[ext] = p

        self._purge_orphans()

        # continue only if both required extensions are present
        return None if {"zs2", "xlsx"} - bucket.keys() else path

    # ---------- record-manager integration ------------------------------------

    def is_valid_datatype(self, path: str) -> bool:
        return Path(path).suffix.lower() in {".zs2", ".xlsx"}

    def matches_file(self, filepath: str) -> bool:
        """Check if this device can process the given file based on extension."""
        return Path(filepath).suffix.lower() in {".zs2", ".xlsx"}

    @classmethod
    def get_device_id(cls) -> str:
        """Get unique device identifier."""
        return "utm_zwick"

    def is_appendable(
        self, record: LocalRecord, filename_prefix: str, extension: str
    ) -> bool:
        # The pair is handled atomically, so once any .xlsx exists we forbid more
        return ".xlsx" not in record.files_uploaded

    # ---------- core processing ------------------------------------------------
    def device_specific_processing(
        self, src_path: str, record_path: str, filename_prefix: str, extension: str
    ):
        raw_prefix = Path(src_path).stem
        bucket = self._pending.pop(raw_prefix, None)
        if bucket is None:
            raise KeyError(f"No staged files for '{raw_prefix}'")

        zs2_path  = bucket["zs2"]
        xlsx_path = bucket["xlsx"]
        record_dir = Path(record_path)

        # 1️⃣  ZIP the raw file
        zip_dest = record_dir / f"{filename_prefix}.zs2.zip"
        try:
            shutil.make_archive(
            base_name=str(zip_dest.with_suffix("")),
            format="zip",
            root_dir=str(zs2_path.parent),
            base_dir=zs2_path.name,
            )
            logger.debug("Archived '%s' → '%s'", zs2_path, zip_dest)
            zs2_path.unlink(missing_ok=True)
        except Exception as e:
            logger.error("Failed to archive '%s': %s", zs2_path, e)
            raise

        # 2️⃣  Move the Excel workbook
        dest_xlsx = get_unique_filename(record_path, filename_prefix, ".xlsx")
        try:
            move_item(xlsx_path, dest_xlsx)
        except Exception as e:
            logger.error("Failed to move '%s' to '%s': %s", xlsx_path, dest_xlsx, e)
            raise

        # 3️⃣  Tell the manager to register *everything* in the folder
        return str(record_dir), "xlsx"

    # ---------- helpers --------------------------------------------------------

    def _purge_orphans(self):
        """Remove staged entries that never received their twin file."""
        now = time.time()
        orphans = [k for k, v in self._pending.items() if now - v["t"] > self._TTL_SECONDS]
        for k in orphans:
            entry = self._pending.pop(k, {})
            for ext, p in entry.items():
                if isinstance(p, Path) and p.exists():
                    try:
                        move_to_exception_folder(p)
                        logger.info("Purged orphan '%s'", p)
                    except Exception as e:
                        logger.warning("Could not purge orphan '%s': %s", p, e)
