from pathlib import Path
import os
from src.records.local_record import LocalRecord
from src.storage.storage_manager import StorageManager
from src.storage.path_manager import PathManager
from src.processing.file_process_manager import BaseFileProcessor
from src.app.logger import setup_logger

logger = setup_logger(__name__)


class SEMFileProcessor(BaseFileProcessor):
    """
    A concrete processor for PhenomXL SEM data (TIFF images or .elid directories).
    """

    def device_specific_preprocessing(self, path: str) -> str:
        p = Path(path)
        if p.suffix.lower() in {".tiff", ".tif"}:
            # Strip trailing digit from the stem, if present.
            new_stem = self._strip_trailing_digit(p.stem)
            if new_stem != p.stem:
                new_path = p.parent / (new_stem + p.suffix)
                p.rename(new_path)
                logger.debug(
                    f"Renamed file: {path} -> {new_path}, removed trailing digit."
                )
                return str(new_path)
        return path

    def _strip_trailing_digit(self, filename: str) -> str:
        """Remove the last character if it is a digit."""
        return filename[:-1] if filename and filename[-1].isdigit() else filename

    def is_valid_datatype(self, path: str) -> bool:
        p = Path(path)
        if p.is_dir():
            # Valid if any direct child file has the '.elid' extension.
            if any(
                child.suffix.lower() == ".elid"
                for child in p.iterdir()
                if child.is_file()
            ):
                return True
        if p.suffix.lower() in {".tiff", ".tif"}:
            return True
        return False

    def is_appendable(
        self, record: LocalRecord, filename_prefix: str, extension: str
    ) -> bool:
        if (
            any(".elid" in key for key in record.files_uploaded.keys())
            or extension == ""
        ):
            return False
        return True

    def device_specific_processing(
        self, src_path: str, record_path: str, filename_prefix: str, extension: str
    ):
        src = Path(src_path)
        record_p = Path(record_path)
        if extension.lower() in {".tif", ".tiff"}:
            # For images, generate a unique filename and move the file.
            new_file_path = PathManager.get_unique_filename(
                record_path, filename_prefix, extension
            )
            StorageManager.move_item(str(src), new_file_path)
            return new_file_path, "img"
        else:
            # Process ELID data.
            self._flatten_elid_directory(src, filename_prefix)
            self._move_remaining_elid_files(src, record_p)
            self._remove_directory(src)
            return record_path, "elid"

    def _flatten_elid_directory(self, folder: Path, filename_prefix: str):
        """
        Recursively flattens the ELID directory by moving and renaming files from subdirectories
        into the root folder (target directory). Uses a helper to ensure filename uniqueness.
        """
        logger.debug(f"Flattening ELID directory: {folder}")
        renamed_files = {}
        target_dir = folder  # Already a Path
        # Walk the directory in bottom-up order.
        for root, dirs, files in os.walk(str(folder), topdown=False):
            root_path = Path(root)
            for fname in files:
                old_path = root_path / fname
                new_fname = self._build_new_filename(fname, root, filename_prefix)
                counter = 1
                original_new_fname = new_fname
                while new_fname in renamed_files or (target_dir / new_fname).exists():
                    name_only = Path(original_new_fname).stem
                    ext = Path(original_new_fname).suffix
                    new_fname = f"{name_only}_{counter}{ext}"
                    counter += 1
                renamed_files[new_fname] = True
                new_path = target_dir / new_fname
                try:
                    StorageManager.move_item(str(old_path), str(new_path))
                    logger.debug(f"Moved and renamed '{old_path}' to '{new_path}'.")
                except OSError as e:
                    logger.error(f"Failed to move '{old_path}' to '{new_path}': {e}")
        logger.debug("Subdirectories flattened for ELID data.")

    def _move_remaining_elid_files(self, src: Path, record_dir: Path):
        """
        Moves any remaining files in the (now flattened) ELID directory to the record directory.
        """
        for child in src.iterdir():
            if child.is_file():
                dest = record_dir / child.name
                StorageManager.move_item(str(child), str(dest))

    def _remove_directory(self, src: Path):
        """
        Attempts to remove the source directory after processing.
        """
        try:
            src.rmdir()
            logger.debug(f"Removed ELID directory: '{src}'.")
        except OSError:
            logger.warning(f"Could not remove ELID directory: '{src}'.")

    def _build_new_filename(
        self, fname: str, root_dir: str, filename_prefix: str
    ) -> str:
        """
        Builds a new filename for files in ELID data.
        Applies different renaming rules depending on the file's extension and its parent directory.
        """
        new_fname = fname
        # If the file is an .elid or .odt file, incorporate the provided filename_prefix.
        if fname.endswith(".elid") or fname.endswith(".odt"):
            ext = Path(fname).suffix
            new_fname = f"{filename_prefix}{ext}"
            new_fname = new_fname.replace(" ", "_")
        # If the file is inside an analysis directory, prefix with that directory name.
        dirname = Path(root_dir).name
        if "analysis" in dirname:
            new_fname = f"{dirname}_{fname}".replace(" ", "_")
            if "analysis" in fname:
                new_fname = fname.replace(" ", "_")
        # If the file is inside an export directory, simply remove spaces.
        if "export" in dirname:
            new_fname = fname.replace(" ", "_")
        return new_fname
