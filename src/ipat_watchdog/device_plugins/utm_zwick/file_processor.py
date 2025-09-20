"""Processor for Zwick/Roell universal testing machine artefacts."""
from __future__ import annotations

from pathlib import Path
import shutil
import time
from typing import Dict

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


class FileProcessorZwickUTM(FileProcessorABS):
    """Handles paired `.zs2` and `.xlsx` files produced by the UTM."""

    _TTL_SECONDS = 60 * 10  # Staged orphan lifetime (seconds)

    def __init__(self) -> None:
        super().__init__()
        self._pending: Dict[str, Dict[str, Path | float]] = {}

    # ------------------------------------------------------------------
    # Pre-processing
    # ------------------------------------------------------------------
    def device_specific_preprocessing(self, path: str) -> str | None:
        p = Path(path)
        prefix = p.stem
        extension = p.suffix.lower().lstrip(".")

        bucket = self._pending.setdefault(prefix, {"t": time.time()})
        bucket[extension] = p

        self._purge_orphans()

        required_extensions = {"zs2", "xlsx"}
        return path if required_extensions.issubset(bucket.keys()) else None

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
        bucket = self._pending.pop(raw_prefix, None)
        if bucket is None:
            raise KeyError(f"No staged files for '{raw_prefix}'")

        zs2_path = Path(bucket["zs2"])
        xlsx_path = Path(bucket["xlsx"])
        record_dir = Path(record_path)

        zip_dest = record_dir / f"{file_id}.zs2.zip"
        try:
            shutil.make_archive(
                base_name=str(zip_dest.with_suffix("")),
                format="zip",
                root_dir=str(zs2_path.parent),
                base_dir=zs2_path.name,
            )
            logger.debug("Archived '%s' to '%s'", zs2_path, zip_dest)
            zs2_path.unlink(missing_ok=True)
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to archive '%s': %s", zs2_path, exc)
            raise

        destination_xlsx = get_unique_filename(record_path, file_id, ".xlsx")
        try:
            move_item(xlsx_path, destination_xlsx)
        except Exception as exc:
            logger.error("Failed to move '%s' to '%s': %s", xlsx_path, destination_xlsx, exc)
            raise

        return ProcessingOutput(final_path=str(record_dir), datatype="xlsx")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _purge_orphans(self) -> None:
        now = time.time()
        expired_keys = [key for key, payload in self._pending.items() if now - payload["t"] > self._TTL_SECONDS]
        for key in expired_keys:
            payload = self._pending.pop(key, {})
            for candidate in payload.values():
                if isinstance(candidate, Path) and candidate.exists():
                    try:
                        move_to_exception_folder(candidate)
                        logger.info("Purged orphan '%s'", candidate)
                    except Exception as exc:  # pragma: no cover - defensive
                        logger.warning("Could not purge orphan '%s': %s", candidate, exc)
