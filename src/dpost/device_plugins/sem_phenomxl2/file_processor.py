"""Processor for PHENOM XL2 SEM artefacts under canonical dpost namespace."""

from __future__ import annotations

import shutil
from pathlib import Path

from dpost.application.config import DeviceConfig
from dpost.application.processing.file_processor_abstract import (
    FileProcessorABS,
    PreprocessingResult,
    ProcessingOutput,
)
from dpost.domain.records.local_record import LocalRecord
from dpost.infrastructure.logging import setup_logger
from dpost.infrastructure.storage.filesystem_utils import get_unique_filename, move_item

logger = setup_logger(__name__)


class FileProcessorSEMPhenomXL2(FileProcessorABS):
    """Normalise TischREM filenames and handle ELID exports."""

    def __init__(self, device_config: DeviceConfig) -> None:
        super().__init__(device_config)

    def device_specific_preprocessing(self, path: str) -> PreprocessingResult:
        candidate = Path(path)
        native_extensions = self.device_config.files.native_extensions
        if candidate.suffix.lower() in native_extensions:
            new_stem = self._strip_trailing_digit(candidate.stem)
            if new_stem != candidate.stem:
                logger.debug(
                    "Normalised TischREM filename from '%s' to '%s'",
                    candidate.name,
                    f"{new_stem}{candidate.suffix}",
                )
                return PreprocessingResult.with_prefix(path, new_stem)
        return PreprocessingResult.passthrough(path)

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

    def device_specific_processing(
        self,
        src_path: str,
        record_path: str,
        file_id: str,
        extension: str,
    ) -> ProcessingOutput:
        src = Path(src_path)
        record_dir = Path(record_path)

        if extension.lower() in {
            ext.lower() for ext in self.device_config.files.native_extensions
        }:
            destination = get_unique_filename(record_path, file_id, extension)
            move_item(src, destination)
            return ProcessingOutput(final_path=destination, datatype="img")

        self._zip_export(src, record_dir, file_id)
        self._move_descriptors(src, record_dir, file_id)
        self._cleanup(src)
        return ProcessingOutput(final_path=str(record_dir), datatype="elid")

    def _zip_export(self, elid_dir: Path, record_dir: Path, base: str) -> Path:
        export_dir = elid_dir / "export"
        if not export_dir.exists():
            logger.warning("No 'export' directory found in %s", elid_dir)
            return record_dir / f"{base}.zip"

        zip_path = record_dir / f"{base}.zip"
        shutil.make_archive(
            str(zip_path.with_suffix("")),
            "zip",
            root_dir=str(export_dir),
        )
        logger.debug("Created ZIP archive '%s' from '%s'", zip_path, export_dir)
        return zip_path

    def _move_descriptors(self, elid_dir: Path, record_dir: Path, base: str) -> None:
        allowed = {
            ext.lower() for ext in self.device_config.files.allowed_folder_contents
        }
        for descriptor in elid_dir.iterdir():
            if not descriptor.is_file():
                continue
            suffix = descriptor.suffix.lower()
            if suffix not in allowed:
                continue
            destination = record_dir / f"{base}{suffix}"
            if destination.exists():
                destination = Path(get_unique_filename(str(record_dir), base, suffix))
            try:
                move_item(str(descriptor), str(destination))
                logger.debug("Moved descriptor '%s' to '%s'", descriptor, destination)
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to move descriptor '%s': %s", descriptor, exc)

    def _cleanup(self, elid_dir: Path) -> None:
        try:
            shutil.rmtree(elid_dir)
            logger.debug("Removed ELID directory '%s'", elid_dir)
        except Exception as exc:  # noqa: BLE001
            logger.error("Could not remove directory '%s': %s", elid_dir, exc)
