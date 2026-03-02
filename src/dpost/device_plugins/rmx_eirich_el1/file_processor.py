"""File processor for RMX EIRICH EL1 text exports under dpost namespace."""

from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path

from dpost.application.config import DeviceConfig
from dpost.application.processing.file_processor_abstract import (
    FileProbeResult,
    FileProcessorABS,
    PreprocessingResult,
    ProcessingOutput,
)
from dpost.domain.records.local_record import LocalRecord
from dpost.infrastructure.storage.filesystem_utils import get_unique_filename, move_item


class FileProcessorEirich(FileProcessorABS):
    """Move Eirich EL1 .txt exports into the record folder."""

    def __init__(self, device_config: DeviceConfig) -> None:
        super().__init__(device_config)
        self.device_config = device_config

    def device_specific_preprocessing(self, path: str) -> PreprocessingResult | None:
        return PreprocessingResult.passthrough(path)

    def probe_file(self, filepath: str) -> FileProbeResult:
        """Identify Eirich files by extension and configured filename patterns."""
        target = Path(filepath)
        ext = target.suffix.lower()
        exported_extensions = self.device_config.files.exported_extensions

        if ext not in exported_extensions:
            return FileProbeResult.mismatch(
                f"Unsupported extension for Eirich mixer: {ext}"
            )
        if not self._matches_filename_pattern(filepath):
            return FileProbeResult.mismatch("Filename did not match Eirich pattern")
        return FileProbeResult.match(
            confidence=0.95,
            reason="Matched Eirich filename pattern",
        )

    def is_appendable(
        self, record: LocalRecord, filename_prefix: str, extension: str
    ) -> bool:
        return True

    @classmethod
    def get_device_id(cls) -> str:
        return "rmx_eirich_el1"

    def device_specific_processing(
        self,
        src_path: str,
        record_path: str,
        file_id: str,
        extension: str,
    ) -> ProcessingOutput:
        destination = get_unique_filename(
            record_path,
            file_id,
            extension,
            id_separator="-",
        )
        move_item(src_path, destination)
        return ProcessingOutput(final_path=destination, datatype="tabular")

    def _matches_filename_pattern(self, filepath: str) -> bool:
        filename = Path(filepath).name.lower()
        patterns = self.device_config.files.filename_patterns
        return any(fnmatch(filename, pattern.lower()) for pattern in patterns)
