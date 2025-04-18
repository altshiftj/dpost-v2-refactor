from pathlib import Path
import os
from records.local_record import LocalRecord
from processing.file_processor_abstract import FileProcessorABS
from storage.filesystem_utils import move_item, get_unique_filename
from app.logger import setup_logger

logger = setup_logger(__name__)


class FileProcessorTischREM(FileProcessorABS):
    """
    A concrete processor for PhenomXL SEM data (TIFF images or .elid directories).
    """

    def device_specific_preprocessing(self, path: str) -> str:
        p = Path(path)
        if p.suffix.lower() in {".tiff", ".tif"}:
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
        return filename[:-1] if filename and filename[-1].isdigit() else filename

    def is_valid_datatype(self, path: str) -> bool:
        p = Path(path)
        if p.is_dir():
            return any(child.suffix.lower() == ".elid" for child in p.iterdir() if child.is_file())
        return p.suffix.lower() in {".tiff", ".tif"}

    def is_appendable(
        self, record: LocalRecord, filename_prefix: str, extension: str
    ) -> bool:
        return not (
            any(".elid" in key for key in record.files_uploaded.keys())
            or extension == ""
        )

    def device_specific_processing(
        self, src_path: str, record_path: str, filename_prefix: str, extension: str
    ):
        src = Path(src_path)
        record_p = Path(record_path)
        if extension.lower() in {".tif", ".tiff"}:
            new_file_path = get_unique_filename(record_path, filename_prefix, extension)
            move_item(src, new_file_path)
            return new_file_path, "img"
        else:
            self._flatten_elid_directory(src, filename_prefix)
            self._move_remaining_elid_files(src, record_p)
            self._remove_directory(src)
            return record_path, "elid"

    def _flatten_elid_directory(self, folder: Path, filename_prefix: str):
        logger.debug(f"Flattening ELID directory: {folder}")
        renamed_files = {}
        target_dir = folder

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
                    move_item(old_path, new_path)
                    logger.debug(f"Moved and renamed '{old_path}' to '{new_path}'.")
                except OSError as e:
                    logger.error(f"Failed to move '{old_path}' to '{new_path}': {e}")

            for d in dirs:
                subdir_path = root_path / d
                try:
                    subdir_path.rmdir()
                    logger.debug(f"Removed empty directory: '{subdir_path}'.")
                except OSError:
                    logger.warning(f"Could not remove directory: '{subdir_path}'.")

        logger.debug("Subdirectories flattened for ELID data.")

    def _move_remaining_elid_files(self, src: Path, record_dir: Path):
        for child in src.iterdir():
            if child.is_file():
                dest = record_dir / child.name
                move_item(child, dest)

    def _remove_directory(self, src: Path):
        try:
            src.rmdir()
            logger.debug(f"Removed ELID directory: '{src}'.")
        except OSError:
            logger.warning(f"Could not remove ELID directory: '{src}'.")

    def _build_new_filename(
        self, fname: str, root_dir: str, filename_prefix: str
    ) -> str:
        new_fname = fname
        if fname.endswith(".elid") or fname.endswith(".odt"):
            ext = Path(fname).suffix
            new_fname = f"{filename_prefix}{ext}".replace(" ", "_")

        dirname = Path(root_dir).name
        if "analysis" in dirname:
            new_fname = f"{dirname}_{fname}".replace(" ", "_")
            if "analysis" in fname:
                new_fname = fname.replace(" ", "_")
        if "export" in dirname:
            new_fname = fname.replace(" ", "_")

        return new_fname
