"""Minimal processor used by automated tests."""

from __future__ import annotations

from pathlib import Path

from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.core.processing.file_processor_abstract import (
    FileProcessorABS,
    ProcessingOutput,
)
from ipat_watchdog.core.records.local_record import LocalRecord
from ipat_watchdog.core.storage.filesystem_utils import get_unique_filename, move_item

logger = setup_logger(__name__)


class TestFileProcessor(FileProcessorABS):
    """Moves files verbatim into the record directory."""

    def device_specific_processing(
        self,
        src_path: str,
        record_path: str,
        filename_prefix: str,
        extension: str,
    ) -> ProcessingOutput:
        destination = get_unique_filename(record_path, filename_prefix, extension)
        move_item(src_path, destination)
        logger.debug("Test processor moved '%s' to '%s'", src_path, destination)
        return ProcessingOutput(final_path=destination, datatype="test")

    def is_appendable(
        self,
        record: LocalRecord,
        filename_prefix: str,
        extension: str,
    ) -> bool:
        return True

    @classmethod
    def get_device_id(cls) -> str:
        return "test_device"

    def matches_file(self, filepath: str) -> bool:
        return Path(filepath).suffix.lower() in {".tif", ".txt"}
