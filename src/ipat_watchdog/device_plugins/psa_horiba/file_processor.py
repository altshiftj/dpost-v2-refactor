from pathlib import Path
import shutil
import os

from ipat_watchdog.core.records.local_record import LocalRecord
from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS
from ipat_watchdog.core.storage.filesystem_utils import (
    move_item,
    get_unique_filename,
)
from ipat_watchdog.core.logging.logger import setup_logger

logger = setup_logger(__name__)


class FileProcessorPSAHoriba(FileProcessorABS):
    """
    Processor for Horiba Partica LA-960 data.
    """

    # ---------- preprocessing --------------------------------------------------

    def device_specific_preprocessing(self, path: str) -> str:
        return path

    # ---------- record-manager integration ------------------------------------

    # is_valid_datatype removed; use matches_file instead

    def is_appendable(
        self, record: LocalRecord, filename_prefix: str, extension: str
    ) -> bool:
        return True

    # ---------- core processing ------------------------------------------------

    def device_specific_processing(
        self, src_path: str, record_path: str, filename_prefix: str, extension: str
    ) -> tuple[str, str]:
        """
        Parameters
        ----------
        src_path : str
            Path of incoming item (file or directory).
        record_path : str
            Destination directory for the record.
        filename_prefix : str
            The <file_id> generated upstream by FileProcessManager.
        extension : str
            File extension of src_path ('' for directories).
        """
        src = Path(src_path)

        dest = get_unique_filename(record_path, filename_prefix, extension)
        move_item(src, dest)

        return str(dest), "psa"
