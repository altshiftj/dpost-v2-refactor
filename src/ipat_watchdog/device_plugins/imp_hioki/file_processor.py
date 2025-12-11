"""Processor for Hioki analyzer exports (Excel only)."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from ipat_watchdog.core.config.schema import DeviceConfig
from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.core.processing.file_processor_abstract import (
    FileProcessorABS,
    FileProbeResult,
    ProcessingOutput,
)
from ipat_watchdog.core.records.local_record import LocalRecord
from ipat_watchdog.core.storage.filesystem_utils import get_unique_filename, move_item

logger = setup_logger(__name__)


class FileProcessorHioki(FileProcessorABS):
    """Export-only: move Excel workbook into the record with a unique name."""

    def __init__(self, device_config: DeviceConfig) -> None:
        super().__init__(device_config)
        self.device_config = device_config

    # No staging/pairing needed
    def device_specific_preprocessing(self, path: str) -> Optional[str]:
        return path

    # Probe: rely on extension
    def probe_file(self, filepath: str) -> FileProbeResult:
        p = Path(filepath)
        ext = p.suffix.lower()

        # Adjust exported_extensions vs allowed_extensions according to your config
        if ext in self.device_config.files.exported_extensions:
            return FileProbeResult.match(
                confidence=0.6,
                reason="Excel export for Hioki analyzer",
            )
        return FileProbeResult.mismatch("Unsupported extension for Hioki (Excel expected)")

    def is_appendable(self, record: LocalRecord, filename_prefix: str, extension: str) -> bool:
        # allow multiple exports in the same record
        return True

    @classmethod
    def get_device_id(cls) -> str:
        return "hioki_blb"

    def device_specific_processing(
        self,
        src_path: str,
        record_path: str,
        filename_prefix: str,
        extension: str,
    ) -> ProcessingOutput:
        """
        Mirror EXTR behaviour: use the already-validated filename_prefix
        and let filesystem_utils generate a unique name in the record folder.
        """
        destination = get_unique_filename(record_path, filename_prefix, extension)
        move_item(src_path, destination)
        return ProcessingOutput(final_path=destination, datatype="hioki")
