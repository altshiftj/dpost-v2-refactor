"""Processor for Phenom-XL SEM artefacts."""
from __future__ import annotations

from pathlib import Path
import shutil

from ipat_watchdog.core.config.schema import DeviceConfig
from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.core.processing.file_processor_abstract import (
    FileProcessorABS,
    ProcessingOutput,
)
from ipat_watchdog.core.records.local_record import LocalRecord
from ipat_watchdog.core.storage.filesystem_utils import get_unique_filename, move_item

logger = setup_logger(__name__)


class FileProcessorSEMPhenomXL2(FileProcessorABS):
    """Normalises TischREM filenames and handles ELID exports."""

    def __init__(self, device_config: DeviceConfig) -> None:
        super().__init__(device_config)
        # Remember temporary normalised names so we can recover the original source when processing.
        self._path_mapping: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Pre-processing
    # ------------------------------------------------------------------
    def device_specific_preprocessing(self, path: str) -> str:
        candidate = Path(path)
        native_exts = self.device_config.files.native_extensions
        if candidate.suffix.lower() in native_exts:
            new_stem = self._strip_trailing_digit(candidate.stem)
            if new_stem != candidate.stem:
                normalized = candidate.with_name(f"{new_stem}{candidate.suffix}")
                self._path_mapping[str(normalized)] = str(candidate)
                logger.debug(
                    "Normalised TischREM filename from '%s' to '%s'",
                    candidate.name,
                    normalized.name,
                )
                return str(normalized)
        return path

    @staticmethod
    def _strip_trailing_digit(filename: str) -> str:
        return filename[:-1] if filename and filename[-1].isdigit() else filename

    def is_appendable(
        self,
        record: LocalRecord,
        filename_prefix: str,
        extension: str,
    ) -> bool:
        allowed_suffixes = tuple(self.device_config.files.allowed_folder_contents)
        return not (
            any(key.endswith(allowed_suffixes) for key in record.files_uploaded.keys())
            or extension == ""
        )

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
        actual_src_path = Path(self._path_mapping.pop(src_path, src_path))
        record_dir = Path(record_path)

        if extension.lower() in {ext.lower() for ext in self.device_config.files.native_extensions}:
            # Native microscope images only need deduplicated moves into the record directory.
            destination = get_unique_filename(record_path, filename_prefix, extension)
            move_item(actual_src_path, destination)
            return ProcessingOutput(final_path=destination, datatype="img")

        zip_path = self._zip_export(actual_src_path, record_dir, filename_prefix)
        self._move_descriptors(actual_src_path, record_dir, filename_prefix)
        self._cleanup(actual_src_path)

        return ProcessingOutput(final_path=str(record_dir), datatype="elid")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _zip_export(self, elid_dir: Path, record_dir: Path, base: str) -> Path:
        export_dir = elid_dir / "export"
        if not export_dir.exists():
            logger.warning("No 'export' directory found in %s", elid_dir)
            return record_dir / f"{base}.zip"

        zip_path = record_dir / f"{base}.zip"
        shutil.make_archive(str(zip_path.with_suffix("")), "zip", root_dir=str(export_dir))
        logger.debug("Created ZIP archive '%s' from '%s'", zip_path, export_dir)
        return zip_path

    def _move_descriptors(self, elid_dir: Path, record_dir: Path, base: str) -> None:
        for descriptor in elid_dir.iterdir():
            if descriptor.is_file() and descriptor.suffix.lower() in {ext.lower() for ext in self.device_config.files.allowed_folder_contents}:
                destination = record_dir / f"{base}{descriptor.suffix.lower()}"
                if destination.exists():
                    destination = Path(get_unique_filename(str(record_dir), base, descriptor.suffix.lower()))
                try:
                    move_item(str(descriptor), str(destination))
                    logger.debug("Moved descriptor '%s' to '%s'", descriptor, destination)
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.error("Failed to move descriptor '%s': %s", descriptor, exc)

    def _cleanup(self, elid_dir: Path) -> None:
        try:
            shutil.rmtree(elid_dir)
            logger.debug("Removed ELID directory '%s'", elid_dir)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Could not remove directory '%s': %s", elid_dir, exc)
