"""File processor for Mischraum extruder Excel exports."""

from __future__ import annotations

from pathlib import Path

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


class FileProcessorEXTRHaake(FileProcessorABS):
    """Moves Excel exports from the Mischraum extruder into the record folder."""
    def __init__(self, device_config: DeviceConfig) -> None:
        super().__init__(device_config)
        self.device_config = device_config

    def probe_file(self, filepath: str) -> FileProbeResult:
        suffix = Path(filepath).suffix.lower()
        if suffix in self.device_config.files.allowed_extensions:
            return FileProbeResult.match(confidence=0.6, reason="Excel export for Mischraum extruder")
        return FileProbeResult.mismatch("Unsupported extension for Mischraum extruder")

    def is_appendable(self, record: LocalRecord, filename_prefix: str, extension: str) -> bool:
        return True

    def device_specific_processing(
        self,
        src_path: str,
        record_path: str,
        filename_prefix: str,
        extension: str,
    ) -> ProcessingOutput:
        destination = get_unique_filename(record_path, filename_prefix, extension)
        move_item(src_path, destination)
        return ProcessingOutput(final_path=destination, datatype="tabular")
