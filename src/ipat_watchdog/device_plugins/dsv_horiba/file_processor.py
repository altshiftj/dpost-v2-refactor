"""Processor for Horiba DSV dissolver batches."""
from __future__ import annotations

from pathlib import Path
import time
import zipfile
from typing import Any, Dict, List

from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.core.processing.file_processor_abstract import (
    FileProcessorABS,
    FileProbeResult,
    ProcessingOutput,
)
from ipat_watchdog.core.config import DeviceConfig
from ipat_watchdog.core.records.local_record import LocalRecord
from ipat_watchdog.core.storage.filesystem_utils import (
    get_unique_filename,
    move_item,
    move_to_exception_folder,
)

logger = setup_logger(__name__)


class FileProcessorDSVHoriba(FileProcessorABS):
    """Aggregates raw (*.wd*) files and exported *.txt reports."""
    def __init__(self, device_config: DeviceConfig) -> None:
        super().__init__(device_config)
        self.device_config = device_config
        self._batches: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Pre-processing
    # ------------------------------------------------------------------
    def device_specific_preprocessing(self, path: str) -> str | None:
        candidate = Path(path)
        key = self._key(candidate)
        bucket = self._batches.setdefault(key, {"files": [], "t": time.time(), "ready": False})

        if candidate not in bucket["files"]:
            bucket["files"].append(candidate)
        bucket["t"] = time.time()

        self._purge_orphans()

        files: List[Path] = bucket["files"]
        native_exts = self.device_config.files.native_extensions
        exported_exts = self.device_config.files.exported_extensions
        has_native = any(f.suffix.lower() in native_exts for f in files)
        has_exported = any(f.suffix.lower() in exported_exts for f in files)

        if not bucket["ready"] and has_native and has_exported:
            bucket["ready"] = True
            logger.debug("Dissolver batch ready for key '%s': %s", key, [str(f) for f in files])
            return path
        return None

    # ------------------------------------------------------------------
    # Probing
    # ------------------------------------------------------------------
    def probe_file(self, filepath: str) -> FileProbeResult:
        """Identify dissolver exports by .txt content; raw WD* are inconclusive.

        Heuristics for .txt:
        - Look for terms like "dissolution", "release", "rpm", "medium",
          or vendor cues like "HORIBA" in header lines.
        """
        path = Path(filepath)
        ext = path.suffix.lower()
        native_exts = self.device_config.files.native_extensions
        exported_exts = self.device_config.files.exported_extensions

        if ext in native_exts:
            return FileProbeResult.unknown("Raw WD* file; probe inconclusive")

        if ext not in exported_exts:
            return FileProbeResult.mismatch("Not a dissolver export text file")

        try:
            snippet = self._read_text_prefix(path)
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("DSV probe failed to read '%s': %s", path, exc)
            return FileProbeResult.unknown(str(exc))

        text = snippet.lower()
        tokens = [
            "dissolution",
            "release",
            "rpm",
            "stirring",
            "medium",
            "horiba",
        ]

        score = sum(1 for t in tokens if t in text)
        if score == 0:
            return FileProbeResult.unknown("No dissolver markers found in TXT")

        confidence = min(0.55 + 0.1 * score, 0.9)
        return FileProbeResult.match(confidence=confidence, reason=f"Found dissolver markers (score={score})")

    @classmethod
    def get_device_id(cls) -> str:
        return "dsv_horiba"

    def is_appendable(
        self,
        record: LocalRecord,
        filename_prefix: str,
        extension: str,
    ) -> bool:
        return True

    # ------------------------------------------------------------------
    # Core processing
    # ------------------------------------------------------------------
    def device_specific_processing(
        self,
        src_path: str,
        record_path: str,
        filename_prefix: str,
        extension: str,
    ) -> ProcessingOutput:
        src = Path(src_path)
        record_dir = Path(record_path)
        key = self._key(src)

        bucket = self._batches.pop(key, None)
        if not bucket:
            destination = get_unique_filename(record_path, filename_prefix, src.suffix.lower())
            move_item(src, destination)
            return ProcessingOutput(final_path=destination, datatype="txt")

        files: List[Path] = bucket["files"]
        raw_exts = {".wdb", ".wdk", ".wdp"}
        raw_files = [candidate for candidate in files if candidate.suffix.lower() in raw_exts]
        txt_files = [candidate for candidate in files if candidate.suffix.lower() == ".txt"]

        if raw_files:
            zip_dest = record_dir / f"{filename_prefix}_raw_data.zip"
            try:
                with zipfile.ZipFile(zip_dest, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for raw_file in raw_files:
                        zip_file.write(raw_file, raw_file.name)
                        logger.debug("Added '%s' to raw archive", raw_file)
                for raw_file in raw_files:
                    try:
                        raw_file.unlink(missing_ok=True)
                    except Exception as exc:  # pragma: no cover - defensive
                        logger.warning("Could not delete raw file '%s': %s", raw_file, exc)
            except Exception as exc:
                logger.error("Failed to archive raw files to '%s': %s", zip_dest, exc)
                raise

        for txt_file in txt_files:
            try:
                destination = get_unique_filename(record_path, filename_prefix, ".txt")
                move_item(str(txt_file), destination)
                logger.debug("Moved txt file '%s' to '%s'", txt_file, destination)
            except Exception as exc:
                logger.error("Failed to move txt file '%s': %s", txt_file, exc)
                raise

        return ProcessingOutput(final_path=str(record_dir), datatype="txt")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _key(path: Path) -> str:
        return path.stem

    @staticmethod
    def _read_text_prefix(path: Path, bytes_limit: int = 4096) -> str:
        raw = path.read_bytes()[:bytes_limit]
        for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
            try:
                return raw.decode(enc, errors="ignore")
            except Exception:
                continue
        return raw.decode(errors="ignore")

    def _purge_orphans(self) -> None:
        now = time.time()
        stale_keys = [
            key
            for key, bucket in self._batches.items()
            if not bucket.get("ready") and now - bucket.get("t", now) > self.device_config.batch.ttl_seconds
        ]
        for key in stale_keys:
            bucket = self._batches.pop(key, {})
            files = bucket.get("files", [])
            logger.warning("Purging stale dissolver batch '%s' with files: %s", key, files)
            for candidate in files:
                if isinstance(candidate, Path) and candidate.exists():
                    try:
                        move_to_exception_folder(candidate)
                        logger.info("Moved orphan file to exceptions: '%s'", candidate)
                    except Exception as exc:  # pragma: no cover - defensive
                        logger.warning("Could not move orphan file '%s': %s", candidate, exc)
