"""File processor for Eirich mixer EL1 text exports."""

from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path
from typing import Optional

from ipat_watchdog.core.config.schema import DeviceConfig
from ipat_watchdog.core.processing.file_processor_abstract import (
    FileProcessorABS,
    FileProbeResult,
    PreprocessingResult,
    ProcessingOutput,
)
from ipat_watchdog.core.records.local_record import LocalRecord
from ipat_watchdog.core.storage.filesystem_utils import get_unique_filename, move_item


class FileProcessorEirich(FileProcessorABS):
    """Moves .txt exports from the Eirich EL1 mixer into the record folder."""

    def __init__(self, device_config: DeviceConfig) -> None:
        super().__init__(device_config)
        self.device_config = device_config

    def device_specific_preprocessing(self, path: str) -> Optional[PreprocessingResult]:
        return PreprocessingResult.passthrough(path)

    def probe_file(self, filepath: str) -> FileProbeResult:
        """
        Identify Eirich mixer files by filename pattern.

        Variant selection is encoded in the filename (e.g. Eirich_EL1_TrendFile_*),
        so a direct match is sufficient to route the file.
        """
        path = Path(filepath)
        ext = path.suffix.lower()
        exported_exts = self.device_config.files.exported_extensions

        if ext not in exported_exts:
            return FileProbeResult.mismatch(f"Unsupported extension for Eirich mixer: {ext}")

        if not self._matches_filename_pattern(filepath):
            return FileProbeResult.mismatch("Filename did not match Eirich pattern")

        return FileProbeResult.match(
            confidence=0.95,
            reason="Matched Eirich filename pattern",
        )

    def is_appendable(self, record: LocalRecord, filename_prefix: str, extension: str) -> bool:
        # Allow multiple .txt exports within the same record
        return True

    @classmethod
    def get_device_id(cls) -> str:
        """Device ID used by the processor factory."""
        return "rmx_eirich_el1"

    def device_specific_processing(
        self,
        src_path: str,
        record_path: str,
        filename_prefix: str,
        extension: str,
    ) -> ProcessingOutput:
        """
        Mirror EXTR/Hioki behaviour: use the already-validated filename_prefix
        and let filesystem_utils generate a unique name in the record folder.
        """
        destination = get_unique_filename(record_path, filename_prefix, extension)
        move_item(src_path, destination)

        # You can change 'datatype' to something more specific if you like,
        # e.g. 'rmx_eirich_el1'; for now it's fine to keep 'tabular' or 'text'.
        return ProcessingOutput(final_path=destination, datatype="tabular")

    def _matches_filename_pattern(self, filepath: str) -> bool:
        """Check if filename matches any configured Eirich naming patterns."""
        filename = Path(filepath).name.lower()
        patterns = self.device_config.files.filename_patterns

        return any(fnmatch(filename, pattern.lower()) for pattern in patterns)
