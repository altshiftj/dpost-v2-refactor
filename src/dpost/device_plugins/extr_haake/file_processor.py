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
        if self._id_separator is None and id_separator is not None:
            self._id_separator = id_separator

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
        destination = get_unique_filename(
            record_path,
            file_id,
            extension,
            id_separator=self._runtime_id_separator(),
        )
        move_item(src_path, destination)
        return ProcessingOutput(final_path=destination, datatype="tabular")

    def _runtime_id_separator(self) -> str:
        return self._id_separator or "-"
