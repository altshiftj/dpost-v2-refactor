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
        if path.lower().endswith(('.tiff', '.tif')):
            basename = os.path.basename(path)
            filename_prefix, extension = os.path.splitext(basename)

            # remove last character added by the PhenomXL software
            if filename_prefix[-1].isdigit():
                filename_prefix = filename_prefix[:-1]
                
                # reconstruct the path
                new_path = os.path.join(os.path.dirname(path), filename_prefix + extension)
                os.rename(path, new_path)
                logger.debug(f"Renamed file: {path} -> {new_path}, removed trailing digit.")
                return new_path
        
        return path

    def is_valid_datatype(self, path: str):
        """
        Checks if path is a TIFF/TIF file or a folder containing .elid files.
        """
        if os.path.isdir(path):
            if any(f.endswith('.elid') for f in os.listdir(path)):
                return True
        if path.lower().endswith(('.tiff', '.tif')):
            return True
        return False

    def is_appendable(self, record: LocalRecord, filename_prefix: str, extension: str) -> bool:
        """
        Disallow appending to records that already represent an ELID directory, or if the item is an ELID datatype.
        """
        if any('.elid' in key for key in record.files_uploaded.keys()) or extension == "":
            return False
        return True

    def device_specific_processing(self, src_path: str, record_path: str, filename_prefix: str, extension: str) -> str:
        """
        For ELID data, flatten subdirectories first.
        For TIF/TIFF, just rename and move the file.
        """
        if extension.lower() in ('.tif', '.tiff'):
            # For images, create a unique filename
            new_file_path = PathManager.get_unique_filename(record_path, filename_prefix, extension)
            StorageManager.move_item(src_path, new_file_path)
            return new_file_path, 'img'
        else:
            self._flatten_elid_directory(src_path, filename_prefix)

            # Move each file in the ELID directory to the record directory
            for file in os.listdir(src_path):
                file_path = os.path.join(src_path, file)
                dest_path = os.path.join(record_path, file)
                StorageManager.move_item(file_path, dest_path)

            # delete the original ELID directory
            try:
                os.rmdir(src_path)
                logger.debug(f"Removed ELID directory: '{src_path}'.")
            except OSError:
                logger.warning(f"Could not remove ELID directory: '{src_path}'.")
                
            return record_path, 'elid'


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
    