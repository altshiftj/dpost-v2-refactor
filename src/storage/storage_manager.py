import os
import shutil

from src.records.local_record import LocalRecord
from src.storage.path_manager import PathManager
from src.app.logger import setup_logger

logger = setup_logger(__name__)

class StorageManager:
    def __init__(self, path_manager: PathManager):
        self.path_manager = path_manager

    def archive_record_files(self, record: LocalRecord):
        record_dir = self.path_manager.get_record_path(record)
        os.makedirs(record_dir, exist_ok=True)

        new_file_uploaded = {}
        for src_path, uploaded in record.file_uploaded.items():
            basename = os.path.basename(src_path)
            dest_path = os.path.join(record_dir, basename)
            if os.path.exists(dest_path):
                new_file_uploaded[dest_path] = uploaded
                continue

            try:
                self.move_item(src_path, dest_path)
                new_file_uploaded[dest_path] = uploaded
                logger.info(f"Archived file '{src_path}' to '{dest_path}'.")
            except Exception as e:
                logger.exception(f"Failed to move file '{src_path}' to '{dest_path}': {e}")
                exception_path = self.path_manager.get_exception_path(basename)
                self.move_item(src_path, exception_path)
                logger.info(f"Moved '{src_path}' to exceptions directory at '{exception_path}'.")

        record.file_uploaded = new_file_uploaded

    def clear_staging_dir(self):
        staging_dir = self.path_manager.staging_dir
        for root, dirs, files in os.walk(staging_dir):
            for file in files:
                try:
                    os.remove(os.path.join(root, file))
                    logger.info(f"Removed file '{os.path.join(root, file)}' from staging.")
                except Exception as e:
                    logger.exception(f"Failed to remove file '{os.path.join(root, file)}' from staging: {e}")
            for dir in dirs:
                try:
                    shutil.rmtree(os.path.join(root, dir))
                    logger.info(f"Removed directory '{os.path.join(root, dir)}' from staging.")
                except Exception as e:
                    logger.exception(f"Failed to remove directory '{os.path.join(root, dir)}' from staging: {e}")

    def move_item(self, src: str, dest: str):
        try:
            os.rename(src, dest)
            logger.info(f"Moved '{src}' to '{dest}' using os.rename.")
        except OSError as e:
            logger.warning(f"os.rename failed for '{src}' to '{dest}': {e}. Attempting shutil.move.")
            try:
                shutil.move(src, dest)
                logger.info(f"Moved '{src}' to '{dest}' using shutil.move.")
            except Exception as e_move:
                logger.error(f"Failed to move '{src}' to '{dest}' using shutil.move: {e_move}.")
                raise e_move  # Re-raise exception after logging

    def move_to_directory(self, path: str, directory: str, log_message: str):
        basename = os.path.basename(path)
        base_name, extension = os.path.splitext(basename)
        unique_dest_path = self.path_manager.get_unique_filename(directory, base_name, extension)
        self.move_item(path, unique_dest_path)
        logger.info(log_message + f" Moved to '{unique_dest_path}'.")


    def move_to_rename_folder(self, path: str, name: str):
        unique_dest_path = self.path_manager.get_unique_filename(self.path_manager.rename_dir, name, '')
        self.move_item(path, unique_dest_path)
        logger.info(f"Moved '{path}' to rename folder at '{unique_dest_path}'.")

    def rename_and_move_elid_files(self, folder_path: str, base_name: str):
        """
        Renames and moves all .elid and .odt files from subdirectories into the main folder,
        eliminates all subdirectories, and ensures all filenames are unique and follow naming conventions.
        
        :param folder_path: Path to the main folder containing subdirectories.
        :param base_name: Base name to use for renaming certain files.
        """
        # Define the target directory (can be the main folder or a new one)
        target_dir = folder_path  # Using the main folder as the target

        # Keep track of renamed files to handle naming conflicts
        renamed_files = {}

        for root, dirs, files in os.walk(folder_path, topdown=False):
            for fname in files:
                old_path = os.path.join(root, fname)
                new_fname = fname  # Initialize with the original filename

                # Handle .elid and .odt files
                if fname.endswith('.elid') or fname.endswith('.odt'):
                    _, ext = os.path.splitext(fname)
                    new_fname = f"{base_name}{ext}"
                    logger.debug(f"Handling .elid/.odt file: {fname} -> {new_fname}")

                # Handle analysis directory renaming
                dirname = os.path.basename(root)
                if 'analysis' in dirname and 'analysis' not in fname:
                    new_fname = f"{dirname}-{fname}".replace(' ', '-').replace('_', '-')
                    logger.debug(f"Handling analysis directory file: {fname} -> {new_fname}")

                # Handle spaces and underscores in filenames
                if " " in new_fname:
                    new_fname = new_fname.replace(' ', '-').replace('_', '-')
                    logger.debug(f"Handling spaces/underscores in filename: {fname} -> {new_fname}")

                # Resolve naming conflicts
                original_new_fname = new_fname
                counter = 1
                while new_fname in renamed_files or os.path.exists(os.path.join(target_dir, new_fname)):
                    name, ext = os.path.splitext(original_new_fname)
                    new_fname = f"{name}_{counter}{ext}"
                    counter += 1
                    logger.debug(f"Naming conflict detected. Trying new filename: {new_fname}")

                renamed_files[new_fname] = True  # Mark this filename as used

                new_path = os.path.join(target_dir, new_fname)

                try:
                    # Move and rename the file
                    shutil.move(old_path, new_path)
                    logger.info(f"Moved and renamed '{old_path}' to '{new_path}'.")
                except Exception as e:
                    logger.error(f"Failed to move and rename '{old_path}' to '{new_path}': {e}")

            # After moving all files, remove the empty directory
            try:
                os.rmdir(root)
                logger.info(f"Removed empty directory: '{root}'.")
            except OSError:
                # Directory not empty or other error
                logger.warning(f"Could not remove directory (not empty or error): '{root}'.")

        logger.info("All files have been moved and subdirectories eliminated.")