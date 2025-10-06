"""File processor for ETR twin-screw extruder Excel exports."""

from __future__ import annotations

from pathlib import Path

from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.core.processing.file_processor_abstract import (
    FileProcessorABS,
    FileProbeResult,
    ProcessingOutput,
)
from ipat_watchdog.core.records.local_record import LocalRecord
from ipat_watchdog.core.storage.filesystem_utils import get_unique_filename, move_item

logger = setup_logger(__name__)


class ETRTwinScrewFileProcessor(FileProcessorABS):
    """Moves Excel exports from the ETR twin-screw extruder into the record folder."""

    SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".xlsm"}

    def matches_file(self, filepath: str) -> bool:  # noqa: D401 - short circuit via suffix
        return Path(filepath).suffix.lower() in self.SUPPORTED_EXTENSIONS

    def probe_file(self, filepath: str) -> FileProbeResult:
        suffix = Path(filepath).suffix.lower()
        if suffix in self.SUPPORTED_EXTENSIONS:
            return FileProbeResult.match(confidence=0.6, reason="Excel export for ETR twin-screw extruder")
        return FileProbeResult.mismatch("Unsupported extension for ETR twin-screw extruder")

    def is_appendable(self, record: LocalRecord, filename_prefix: str, extension: str) -> bool:
        # Extruder runs are single exports that should not be appended to an existing record.
        return False

    def device_specific_processing(
        self,
        src_path: str,
        record_path: str,
        filename_prefix: str,
        extension: str,
    ) -> ProcessingOutput:
        destination = get_unique_filename(record_path, filename_prefix, extension)
        move_item(src_path, destination)
        logger.info(
            "ETR twin-screw extruder file moved", extra={"source": src_path, "destination": destination}
        )
        return ProcessingOutput(final_path=destination, datatype="etr-excel")
