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


class FileProcessorTischREM(FileProcessorABS):
    """
    Processor for Phenom-XL SEM data.

    • TIFF images are renamed (if needed) and moved to the record directory.
    • ELID directories are processed by:
        – Zipping their 'export' subfolder into <file_id>.zip.
        – Renaming/moving .odt and .elid to <file_id>.odt / <file_id>.elid.
        – Cleaning up the original ELID directory.
    """

    # ---------- preprocessing --------------------------------------------------

    def device_specific_preprocessing(self, path: str) -> str:
        """
        Remove trailing digits from TischREM files to normalize naming.
        
        TischREM device automatically adds trailing digits (usually "1") to filenames,
        but we want to handle incrementing ourselves through get_unique_filename.
        
        This step normalizes the filename for record identification purposes,
        but keeps the original file in place for later processing.
        """
        p = Path(path)
        if p.suffix.lower() in {".tiff", ".tif"}:
            new_stem = self._strip_trailing_digit(p.stem)
            if new_stem != p.stem:
                # Store the original path for later use in device_specific_processing
                normalized_path = p.parent / (new_stem + p.suffix)
                # Store mapping from normalized path to original path
                if not hasattr(self, '_path_mapping'):
                    self._path_mapping = {}
                self._path_mapping[str(normalized_path)] = str(p)
                logger.debug("Normalized filename from '%s' to '%s' (removed trailing digit)", p.name, normalized_path.name)
                return str(normalized_path)
        return path

    def _strip_trailing_digit(self, filename: str) -> str:
        """Remove trailing digit added by TischREM device (e.g., 'sample1' -> 'sample')"""
        return filename[:-1] if filename and filename[-1].isdigit() else filename

    # ---------- record-manager integration ------------------------------------

    def is_valid_datatype(self, path: str) -> bool:
        p = Path(path)
        if p.is_dir():
            return any(c.suffix.lower() == ".elid" for c in p.iterdir() if c.is_file())
        return p.suffix.lower() in {".tiff", ".tif"}

    def is_appendable(
        self, record: LocalRecord, filename_prefix: str, extension: str
    ) -> bool:
        return not (
            any(".elid" in key for key in record.files_uploaded.keys())
            or extension == ""
        )

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
        record_dir = Path(record_path)
        
        # For TischREM, src_path should be the original file path
        # The device_specific_preprocessing normalizes for record identification
        # but device_specific_processing should work with the original path
        actual_src = src

        # -- 1. Plain TIFF images ------------------------------------------------
        if extension.lower() in {".tif", ".tiff"}:
            dest = get_unique_filename(record_path, filename_prefix, extension)
            move_item(actual_src, dest)
            return dest, "img"

        # -- 2. ELID directory ---------------------------------------------------
        zip_path = self._zip_export(actual_src, record_dir, filename_prefix)
        self._move_descriptors(actual_src, record_dir, filename_prefix)
        self._cleanup(actual_src)

        # Return the record directory so RecordManager walks it and registers
        # the ZIP *and* the renamed descriptor files.
        return str(record_dir), "elid"

    # ---------- helpers --------------------------------------------------------

    def _zip_export(self, elid_dir: Path, record_dir: Path, base: str) -> Path:
        """Create <base>.zip from the folder's export/ subdirectory."""
        export_dir = elid_dir / "export"
        if not export_dir.exists():
            logger.warning("No 'export' directory found in %s – nothing to zip", elid_dir)
            return record_dir / f"{base}.zip"

        zip_path = record_dir / f"{base}.zip"
        shutil.make_archive(str(zip_path.with_suffix("")), "zip", root_dir=str(export_dir))
        logger.debug("Created ZIP archive '%s' from '%s'", zip_path, export_dir)
        return zip_path

    def _move_descriptors(self, elid_dir: Path, record_dir: Path, base: str):
        """
        Move and *rename* .odt / .elid files to <base>.odt / <base>.elid.
        Uses get_unique_filename if a clash is detected (very rare).
        """
        for f in elid_dir.iterdir():
            if f.is_file() and f.suffix.lower() in {".odt", ".elid"}:
                dest = record_dir / f"{base}{f.suffix.lower()}"
                if dest.exists():
                    dest = Path(get_unique_filename(str(record_dir), base, f.suffix.lower()))
                try:
                    move_item(str(f), str(dest))
                    logger.debug("Moved descriptor '%s' → '%s'", f, dest)
                except Exception as e:
                    logger.error("Failed to move descriptor '%s': %s", f, e)

    def _cleanup(self, elid_dir: Path):
        """Remove the original ELID directory once everything is copied."""
        try:
            shutil.rmtree(elid_dir)
            logger.debug("Removed ELID directory '%s'", elid_dir)
        except Exception as e:
            logger.error("Could not remove directory '%s': %s", elid_dir, e)
