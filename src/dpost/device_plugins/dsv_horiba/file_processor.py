"""Processor for DSV HORIBA dissolver batches under canonical dpost namespace."""

from __future__ import annotations

import time
import zipfile
from pathlib import Path
from typing import Any

from dpost.application.config import DeviceConfig
from dpost.application.processing.file_processor_abstract import (
    FileProbeResult,
    FileProcessorABS,
    PreprocessingResult,
    ProcessingOutput,
)
from dpost.domain.processing.text import read_text_prefix
from dpost.domain.records.local_record import LocalRecord
from dpost.infrastructure.logging import setup_logger
from dpost.infrastructure.storage.filesystem_utils import (
    get_unique_filename,
    move_item,
    move_to_exception_folder,
)

logger = setup_logger(__name__)


class FileProcessorDSVHoriba(FileProcessorABS):
    """Aggregate raw WD* files and exported TXT reports."""

    def __init__(self, device_config: DeviceConfig) -> None:
        super().__init__(device_config)
        self.device_config = device_config
        self._batches: dict[str, dict[str, Any]] = {}
        self._exception_dir: str | None = None
        self._id_separator: str | None = None

    def configure_runtime_context(
        self,
        *,
        id_separator: str | None = None,
        filename_pattern=None,
        dest_dir: str | None = None,
        rename_dir: str | None = None,
        exception_dir: str | None = None,
        current_device=None,
    ) -> None:
        """Capture exception-folder and naming context after runtime composition."""
        if self._id_separator is None and id_separator is not None:
            self._id_separator = id_separator
        if self._exception_dir is None and exception_dir is not None:
            self._exception_dir = exception_dir

    def device_specific_preprocessing(self, path: str) -> PreprocessingResult | None:
        candidate = Path(path)
        key = self._key(candidate)
        bucket = self._batches.setdefault(
            key, {"files": [], "t": time.time(), "ready": False}
        )

        if candidate not in bucket["files"]:
            bucket["files"].append(candidate)
        bucket["t"] = time.time()

        self._purge_orphans()

        files: list[Path] = bucket["files"]
        native_extensions = self.device_config.files.native_extensions
        exported_extensions = self.device_config.files.exported_extensions
        has_native = any(path.suffix.lower() in native_extensions for path in files)
        has_exported = any(path.suffix.lower() in exported_extensions for path in files)

        if not bucket["ready"] and has_native and has_exported:
            bucket["ready"] = True
            logger.debug(
                "Dissolver batch ready for key '%s': %s",
                key,
                [str(path) for path in files],
            )
            return PreprocessingResult.passthrough(path)
        return None

    def probe_file(self, filepath: str) -> FileProbeResult:
        """Identify dissolver exports by TXT content; raw WD* files are unknown."""
        path = Path(filepath)
        ext = path.suffix.lower()
        native_extensions = self.device_config.files.native_extensions
        exported_extensions = self.device_config.files.exported_extensions

        if ext in native_extensions:
            return FileProbeResult.unknown("Raw WD* file; probe inconclusive")
        if ext not in exported_extensions:
            return FileProbeResult.mismatch("Not a dissolver export text file")

        try:
            snippet = read_text_prefix(
                path,
                encodings=("utf-8-sig", "utf-8", "latin-1", "cp1252"),
                errors="ignore",
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("DSV probe failed to read '%s': %s", path, exc)
            return FileProbeResult.unknown(str(exc))

        text = snippet.lower()
        tokens = ("dissolution", "release", "rpm", "stirring", "medium", "horiba")
        score = sum(1 for token in tokens if token in text)
        if score == 0:
            return FileProbeResult.unknown("No dissolver markers found in TXT")

        confidence = min(0.55 + 0.1 * score, 0.9)
        return FileProbeResult.match(
            confidence=confidence,
            reason=f"Found dissolver markers (score={score})",
        )

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

    def device_specific_processing(
        self,
        src_path: str,
        record_path: str,
        file_id: str,
        extension: str,
    ) -> ProcessingOutput:
        src = Path(src_path)
        record_dir = Path(record_path)
        key = self._key(src)

        bucket = self._batches.pop(key, None)
        if not bucket:
            destination = get_unique_filename(
                record_path,
                file_id,
                src.suffix.lower(),
                id_separator=self._resolve_id_separator(),
            )
            move_item(str(src), destination)
            return ProcessingOutput(final_path=destination, datatype="txt")

        files: list[Path] = bucket["files"]
        raw_extensions = {".wdb", ".wdk", ".wdp"}
        raw_files = [path for path in files if path.suffix.lower() in raw_extensions]
        txt_files = [path for path in files if path.suffix.lower() == ".txt"]

        if raw_files:
            zip_dest = record_dir / f"{file_id}_raw_data.zip"
            with zipfile.ZipFile(zip_dest, "w", zipfile.ZIP_DEFLATED) as archive:
                for raw_file in raw_files:
                    archive.write(raw_file, raw_file.name)
                    logger.debug("Added '%s' to raw archive", raw_file)
            for raw_file in raw_files:
                try:
                    raw_file.unlink(missing_ok=True)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Could not delete raw file '%s': %s", raw_file, exc)

        for txt_file in txt_files:
            destination = get_unique_filename(
                record_path,
                file_id,
                ".txt",
                id_separator=self._resolve_id_separator(),
            )
            move_item(str(txt_file), destination)
            logger.debug("Moved txt file '%s' to '%s'", txt_file, destination)

        return ProcessingOutput(final_path=str(record_dir), datatype="txt")

    @staticmethod
    def _key(path: Path) -> str:
        return path.stem

    def _purge_orphans(self) -> None:
        now = time.time()
        stale_keys = [
            key
            for key, bucket in self._batches.items()
            if (
                not bucket.get("ready")
                and now - bucket.get("t", now) > self.device_config.batch.ttl_seconds
            )
        ]
        for key in stale_keys:
            bucket = self._batches.pop(key, {})
            files = bucket.get("files", [])
            logger.warning(
                "Purging stale dissolver batch '%s' with files: %s", key, files
            )
            for candidate in files:
                if isinstance(candidate, Path) and candidate.exists():
                    try:
                        move_to_exception_folder(
                            str(candidate),
                            base_dir=self._exception_dir or str(candidate.parent),
                            id_separator=self._resolve_id_separator(),
                        )
                        logger.info("Moved orphan file to exceptions: '%s'", candidate)
                    except Exception as exc:  # noqa: BLE001
                        logger.warning(
                            "Could not move orphan file '%s': %s", candidate, exc
                        )

    def _resolve_id_separator(self) -> str:
        if self._id_separator is not None:
            return self._id_separator
        raise RuntimeError("DSV id_separator runtime context is not configured")
