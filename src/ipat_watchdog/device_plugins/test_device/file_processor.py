# ipat_watchdog/device_plugins/test_device/file_processor.py
from pathlib import Path

from ipat_watchdog.core.records.local_record import LocalRecord
from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS
from ipat_watchdog.core.storage.filesystem_utils import (
    move_item,
    get_unique_filename,
)
from ipat_watchdog.core.logging.logger import setup_logger

logger = setup_logger(__name__)


class TestFileProcessor(FileProcessorABS):
    """
    Simple test file processor that moves files without complex transformations.
    Useful for testing the file processing pipeline without device-specific logic.
    """

    # ---------- preprocessing --------------------------------------------------

    def device_specific_preprocessing(self, path: str) -> str:
        """No special preprocessing for test files."""
        return path

    # ---------- record-manager integration ------------------------------------

    def is_valid_datatype(self, path: str) -> bool:
        """Accept .tif and .txt files for testing."""
        return Path(path).suffix.lower() in {".tif", ".txt"}

    def is_appendable(
        self, record: LocalRecord, filename_prefix: str, extension: str
    ) -> bool:
        """Always allow appending for test files."""
        return True

    # ---------- core processing ------------------------------------------------

    def device_specific_processing(
        self, src_path: str, record_path: str, filename_prefix: str, extension: str
    ) -> tuple[str, str]:
        """
        Simple processing: move file to record directory with unique name.
        
        Parameters
        ----------
        src_path : str
            Path of incoming file.
        record_path : str
            Destination directory for the record.
        filename_prefix : str
            The file_id generated upstream by FileProcessManager.
        extension : str
            File extension of src_path.
        """
        src = Path(src_path)
        
        # Generate unique destination filename
        dest = get_unique_filename(record_path, filename_prefix, extension)
        
        # Move the file
        move_item(src, dest)
        
        # Return the destination and a generic datatype
        return str(dest), "test"

    @classmethod
    def get_device_id(cls) -> str:
        """Get unique device identifier."""
        return "test_device"

    def matches_file(self, filepath: str) -> bool:
        """Check if this device can process the given file based on extension."""
        return Path(filepath).suffix.lower() in {".tif", ".txt"}
