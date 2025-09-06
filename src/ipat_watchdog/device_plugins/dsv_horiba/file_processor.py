# ipat_watchdog/device_plugins/dsv_horiba/file_processor.py
from __future__ import annotations

from pathlib import Path
import shutil
import zipfile
import time
from typing import Dict, Any, List

from ipat_watchdog.core.records.local_record import LocalRecord
from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS
from ipat_watchdog.core.storage.filesystem_utils import (
    move_item,
    move_to_exception_folder,
    get_unique_filename,
)
from ipat_watchdog.core.logging.logger import setup_logger

logger = setup_logger(__name__)


class FileProcessorDSVHoriba(FileProcessorABS):
    """
    Processor for Horiba Dissolver data.

    Workflow
    --------
    1. The dissolver writes raw data files (.wdb, .wdk, .wdp) automatically
    2. Students manually export .txt files with processed results
    3. Files arrive at different times and are grouped by basename
    4. Raw files are compressed into a ZIP archive
    5. Text files are moved as-is to the record
    """

    # ──────────────────────────────────────────────────────────────────────────
    # staging buffer (basename → {"files": [Path, ...], "t": float, "ready": bool})
    # ──────────────────────────────────────────────────────────────────────────
    _TTL_SECONDS: int = 60 * 30  # 30 minutes - longer wait for manual exports

    def __init__(self):
        super().__init__()
        self._batches: Dict[str, Dict[str, Any]] = {}

    # ---------- preprocessing --------------------------------------------------

    def device_specific_preprocessing(self, path: str) -> str | None:
        """
        Stage files by basename until we have both raw data and txt export.
        Return None to pause the flow; return path once to trigger processing.
        """
        p = Path(path)
        key = self._key(p)
        bucket = self._batches.setdefault(key, {"files": [], "t": time.time(), "ready": False})

        # add/update
        if p not in bucket["files"]:
            bucket["files"].append(p)
        bucket["t"] = time.time()

        self._purge_orphans()

        # Check if we have both raw data and exported txt
        raw_exts = {".wdb", ".wdk", ".wdp"}
        files: List[Path] = bucket["files"]
        has_raw = any(f.suffix.lower() in raw_exts for f in files)
        has_txt = any(f.suffix.lower() == ".txt" for f in files)

        if not bucket["ready"] and has_raw and has_txt:
            bucket["ready"] = True
            logger.debug("Dissolver batch ready for key '%s': %s", key, [str(f) for f in files])
            return path  # trigger the rest of the flow exactly once

        # keep waiting for the rest of the batch
        return None

    # ---------- record-manager integration ------------------------------------

    def is_valid_datatype(self, path: str) -> bool:
        # Accept raw data and txt files as valid inputs
        return Path(path).suffix.lower() in {".wdb", ".wdk", ".wdp", ".txt"}

    def matches_file(self, filepath: str) -> bool:
        """Check if this device can process the given file based on extension."""
        return Path(filepath).suffix.lower() in {".wdb", ".wdk", ".wdp", ".txt"}

    @classmethod
    def get_device_id(cls) -> str:
        """Get unique device identifier."""
        return "dsv_horiba"

    def is_appendable(self, record: LocalRecord, filename_prefix: str, extension: str) -> bool:
        # Allow appending by default - different samples can have different basenames
        return True

    # ---------- core processing ------------------------------------------------

    def device_specific_processing(
        self, src_path: str, record_path: str, filename_prefix: str, extension: str
    ) -> tuple[str, str]:
        """
        Process the staged batch: compress raw files to ZIP, move txt files as-is.
        """
        src = Path(src_path)
        record_dir = Path(record_path)
        key = self._key(src)

        bucket = self._batches.pop(key, None)
        if not bucket:
            # Fallback: single-file move if we lost the batch (should be rare)
            dest = get_unique_filename(record_path, filename_prefix, src.suffix.lower())
            move_item(src, dest)
            return str(dest), "txt"

        files: List[Path] = bucket["files"]
        raw_exts = {".wdb", ".wdk", ".wdp"}
        
        # Separate raw files from txt files
        raw_files = [f for f in files if f.suffix.lower() in raw_exts]
        txt_files = [f for f in files if f.suffix.lower() == ".txt"]

        # 1️⃣ Compress raw files into a ZIP archive
        if raw_files:
            zip_dest = record_dir / f"{filename_prefix}_raw_data.zip"
            try:
                with zipfile.ZipFile(zip_dest, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for raw_file in raw_files:
                        # Add file to ZIP with just the filename (no path)
                        zipf.write(raw_file, raw_file.name)
                        logger.debug("Added '%s' to ZIP archive", raw_file)
                
                logger.debug("Created raw data archive: '%s'", zip_dest)
                
                # Remove original raw files after successful archiving
                for raw_file in raw_files:
                    try:
                        raw_file.unlink(missing_ok=True)
                    except Exception as e:
                        logger.warning("Could not remove raw file '%s': %s", raw_file, e)
                        
            except Exception as e:
                logger.error("Failed to create ZIP archive '%s': %s", zip_dest, e)
                raise

        # 2️⃣ Move txt files as-is
        for txt_file in txt_files:
            try:
                dest = get_unique_filename(record_path, filename_prefix, ".txt")
                move_item(str(txt_file), dest)
                logger.debug("Moved txt file '%s' → '%s'", txt_file, dest)
            except Exception as e:
                logger.error("Failed to move txt file '%s': %s", txt_file, e)
                raise

        # 3️⃣ Return the directory so RecordManager indexes all created files
        return str(record_dir), "txt"

    # ---------- helpers --------------------------------------------------------

    def _key(self, p: Path) -> str:
        """Group files by basename without extension."""
        return p.stem

    def _purge_orphans(self):
        """Remove staged entries that never received their complete batch."""
        now = time.time()
        stale = [
            k for k, b in self._batches.items()
            if not b.get("ready") and now - b.get("t", now) > self._TTL_SECONDS
        ]
        for k in stale:
            bucket = self._batches.pop(k, {})
            files = bucket.get("files", [])
            logger.warning("Purging stale dissolver batch '%s' with files: %s", k, files)
            for f in files:
                if isinstance(f, Path) and f.exists():
                    try:
                        move_to_exception_folder(f)
                        logger.info("Moved orphan file to exceptions: '%s'", f)
                    except Exception as e:
                        logger.warning("Could not move orphan file '%s': %s", f, e)
