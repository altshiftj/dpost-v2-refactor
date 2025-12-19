"""File processor for Eirich mixer text exports."""

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


class FileProcessorEirich(FileProcessorABS):
    """Moves .txt exports from the Eirich mixer into the record folder."""

    def __init__(self, device_config: DeviceConfig) -> None:
        super().__init__(device_config)
        self.device_config = device_config

    # No staging/pairing needed for simple text exports
    def device_specific_preprocessing(self, path: str) -> Optional[str]:
        return path

    def probe_file(self, filepath: str) -> FileProbeResult:
        """
        Decide whether this processor should handle the file.

        We rely on the file extension and the device's configured
        exported_extensions (here: .txt).
        """
        suffix = Path(filepath).suffix.lower()
        exported_exts = self.device_config.files.exported_extensions

        if suffix in exported_exts:
            return FileProbeResult.match(
                confidence=0.6,
                reason="Text export for Eirich mixer",
            )
        return FileProbeResult.mismatch("Unsupported extension for Eirich mixer (TXT expected)")

    def is_appendable(self, record: LocalRecord, filename_prefix: str, extension: str) -> bool:
        # Allow multiple .txt exports within the same record
        return True

    @classmethod
    def get_device_id(cls) -> str:
        """
        Device ID used by the processor factory.

        This should match the identifier you use in the config, e.g. 'mix_eirich'.
        """
        return "mix_eirich"

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
        # e.g. 'mix_eirich'; for now it's fine to keep 'tabular' or 'text'.
        return ProcessingOutput(final_path=destination, datatype="tabular")
