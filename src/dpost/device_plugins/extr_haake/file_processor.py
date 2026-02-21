"""Processor for EXTR HAAKE Excel exports under canonical dpost namespace."""

from __future__ import annotations

from pathlib import Path

from dpost.application.config import DeviceConfig
from dpost.application.processing.file_processor_abstract import (
    FileProbeResult,
    FileProcessorABS,
    ProcessingOutput,
)
from dpost.domain.records.local_record import LocalRecord
from dpost.infrastructure.logging import setup_logger
from dpost.infrastructure.storage.filesystem_utils import get_unique_filename, move_item

logger = setup_logger(__name__)


class FileProcessorEXTRHaake(FileProcessorABS):
    """Move extruder Excel artefacts into the selected record folder."""

    def __init__(self, device_config: DeviceConfig) -> None:
        super().__init__(device_config)
        self.device_config = device_config

    def probe_file(self, filepath: str) -> FileProbeResult:
        suffix = Path(filepath).suffix.lower()
        if suffix in self.device_config.files.allowed_extensions:
            return FileProbeResult.match(
                confidence=0.6,
                reason="Excel export for Mischraum extruder",
            )
        return FileProbeResult.mismatch("Unsupported extension for Mischraum extruder")

    def is_appendable(
        self, record: LocalRecord, filename_prefix: str, extension: str
    ) -> bool:
        return True

    def device_specific_processing(
        self,
        src_path: str,
        record_path: str,
        file_id: str,
        extension: str,
    ) -> ProcessingOutput:
        destination = get_unique_filename(record_path, file_id, extension)
        move_item(src_path, destination)
        return ProcessingOutput(final_path=destination, datatype="tabular")
