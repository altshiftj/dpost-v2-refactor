import os
from src.records.local_record import LocalRecord
from src.storage.storage_manager import StorageManager
from src.storage.path_manager import PathManager
from src.processing.file_processor import BaseFileProcessor
from src.app.logger import setup_logger

logger = setup_logger(__name__)

class SEMFileProcessor(BaseFileProcessor):
    """
    A concrete processor for PhenomXL SEM data (TIFF images or .elid directories).
    """

    def is_valid_datatype(self, path: str):
        """
        Checks if path is a TIFF/TIF file or a folder containing .elid files.
        """
        if os.path.isdir(path):
            if any(f.endswith('.elid') for f in os.listdir(path)):
                return True, 'ELID'
        if path.lower().endswith(('.tiff', '.tif')):
            return True, 'IMG'
        return False, None

    def is_record_appendable(self, record: LocalRecord) -> bool:
        """
        Disallow appending to records that already represent an ELID directory.
        """
        if 'elid' in record.long_id:
            return False
        return True

    def device_specific_processing(self, record_path, file_id, src_path, filename_prefix, extension):
        """
        For ELID data, flatten subdirectories first.
        For TIF/TIFF, just rename and move the file.
        """
        if self.item_data_type == 'ELID':
            self._flatten_elid_directory(src_path, filename_prefix)
            new_dir_path = os.path.join(record_path, file_id)
            StorageManager.move_item(src_path, new_dir_path)
            return new_dir_path
        else:
            # For images, create a unique filename
            new_file_path = PathManager.get_unique_filename(record_path, file_id, extension)
            StorageManager.move_item(src_path, new_file_path)
            return new_file_path

    def _flatten_elid_directory(self, folder_path: str, filename_prefix: str):
        """
        Eliminates subdirectories, renames .elid/.odt, etc. in-place.
        """
        logger.debug(f"Flattening ELID directory: {folder_path}")
        target_dir = folder_path
        renamed_files = {}

        for root, dirs, files in os.walk(folder_path, topdown=False):
            for fname in files:
                old_path = os.path.join(root, fname)
                new_fname = self._build_new_filename(fname, root, filename_prefix)
                
                # Ensure uniqueness
                counter = 1
                original_new_fname = new_fname
                while (new_fname in renamed_files or 
                       os.path.exists(os.path.join(target_dir, new_fname))):
                    name_only, ext = os.path.splitext(original_new_fname)
                    new_fname = f"{name_only}_{counter}{ext}"
                    counter += 1

                renamed_files[new_fname] = True
                new_path = os.path.join(target_dir, new_fname)

                try:
                    StorageManager.move_item(old_path, new_path)
                    logger.debug(f"Moved and renamed '{old_path}' to '{new_path}'.")
                except OSError as e:
                    logger.error(f"Failed to move '{old_path}' to '{new_path}': {e}")

            # Remove the subdirectory if empty
            if root != folder_path:
                try:
                    os.rmdir(root)
                    logger.debug(f"Removed empty directory: '{root}'.")
                except OSError:
                    logger.warning(f"Could not remove directory (not empty): '{root}'.")

        logger.debug("Subdirectories flattened for ELID data.")

    def _build_new_filename(self, fname: str, root_dir: str, filename_prefix: str) -> str:
        """
        Builds a new file name for .elid/.odt files or files in analysis/export folders.
        """
        # Default: keep original
        new_fname = fname

        # If .elid/.odt: incorporate base_name
        if fname.endswith('.elid') or fname.endswith('.odt'):
            _, ext = os.path.splitext(fname)
            new_fname = f"{filename_prefix}{ext}"
            new_fname = new_fname.replace(' ', '_')

        # If inside an analysis directory, prefix that folder name
        dirname = os.path.basename(root_dir)
        if 'analysis' in dirname:
            new_fname = f"{dirname}_{fname}".replace(' ', '_')
            if 'analysis' in fname:
                new_fname = fname.replace(' ', '_')

        # If inside an export directory, do a simpler rename
        if 'export' in dirname:
            new_fname = fname.replace(' ', '_')

        return new_fname