"""
file_processor.py

This module contains classes for processing and organizing files within the
data-watchdog system. The classes handle file validation, renaming, moving,
and tying them to existing or new records. They also manage interactions
between sessions, storage operations, and database synchronization.

Classes:
    BaseFileProcessor (abstract):
        Defines the common logic and interface for processing files (or folders)
        and linking them to local records.

    SEMFileProcessor:
        A specific implementation of BaseFileProcessor that handles SEM data types
        (e.g., TIFF images, .elid directories) with custom file/folder handling.
"""

from abc import ABC, abstractmethod
import os
import time

from src.processing.metadata_extractor import MetadataExtractor
from src.storage.storage_manager import IStorageManager
from src.storage.path_manager import PathManager
from src.records.record_manager import RecordManager
from src.records.record_persistence import RecordPersistence
from src.records.id_generator import IdGenerator
from src.gui.user_interface import UserInterface
from src.sessions.session_controller import SessionController
from src.sessions.session_manager import SessionManager
from kadi_apy import KadiManager
from src.app.logger import setup_logger

logger = setup_logger(__name__)

class BaseFileProcessor(ABC):
    """
    An abstract class that defines the shared logic and interface for
    processing files (or directories) and tying them to local records
    within the watch-dog application. It enforces a method to check file
    validity and one to handle device-specific processing.

    Typical workflow:
      1. Check if the incoming file/directory is valid for processing.
      2. If invalid, move it to the exceptions directory.
      3. If valid, determine if it should be appended to an existing record or create a new record.
      4. Perform device-specific file moves/renames.
      5. Optionally sync records to the database if needed.
    """

    def __init__(
        self,
        ui:                 UserInterface,
        session_controller: SessionController,
        paths:              PathManager,
        storage:            IStorageManager,
        persistence:        RecordPersistence,
        ids:                IdGenerator,
        records:            RecordManager,
    ):
        """
        Initializes the BaseFileProcessor.

        :param ui: The GUI manager for user prompts and messaging.
        :param session_manager: Manages user sessions (start, stop, timeout).
        :param session_controller: Orchestrates session behavior (starts new sessions, resets timers).
        :param paths: Manages file paths and naming conventions.
        :param storage: Handles file/directory moving and renaming.
        :param persistence: Responsible for loading/saving record data to disk.
        :param ids: Generates and parses record/file IDs based on naming conventions.
        :param sync: Syncs records to a remote database or system.
        :param records: Manages in-memory record objects, creation, and updating.
        """
        self.ui:                    UserInterface       = ui
        self.session_controller:    SessionController   = session_controller
        self.paths:                 PathManager         = paths
        self.storage:               IStorageManager     = storage
        self.persistence:           RecordPersistence   = persistence
        self.ids:                   IdGenerator         = ids
        self.records:               RecordManager       = records

        # If any record is not fully uploaded, do an initial sync on startup:
        if not self.records.all_records_uploaded():
            logger.info("Syncing records to database upon startup.")
            self.sync_records_to_database()
            # Reset the dictionary date if needed
            if not self.records.is_dict_up_to_date():
                self.records.reset_dict()

        # Will hold the data type for the item being processed
        self.item_data_type = None

    @abstractmethod
    def is_valid_datatype(self, path: str):
        """
        Checks if the file/folder at the given path is valid for this device or file processor.
        Should return a tuple of (bool, str | None):
            - bool: indicating if the file is valid
            - str | None: describing the type of data or None if invalid
        """
        pass

    def process_item(self, path: str):
        """
        Main entry point for processing a new or modified file/directory.

        :param path: The path to the file or directory to process.
        """
        name = os.path.basename(path)          # Extract the file/folder name
        extension = os.path.splitext(name)[1]  # e.g. ".tif"

        # Validate and get the data type (e.g., 'IMG', 'ELID', etc.)
        valid, self.item_data_type = self.is_valid_datatype(path)
        if not valid:
            # If invalid, move to the exceptions directory
            exception_path = self.paths.get_exception_path(name)
            self.storage.move_item(path, exception_path)
            logger.info(f"Moved '{name}' to exceptions directory.")
            return

        # If valid, route it based on record name and state
        self.route_item_via_name(name, extension, path)
    
    def route_item_via_name(self, name, extension, path):
        """
        Determines how to handle the item based on its 'short_id' (i.e., base_name).
        Decides if it belongs to an existing record, a new record, or if the naming
        convention is invalid (triggering rename prompts).

        :param name: The file or folder name with extension.
        :param extension: The extension part of the name, e.g., '.tif' or ''.
        :param path: The full path to the file or folder.
        """
        # Initially ensure the record dictionary is for the current date
        if not self.records.is_dict_up_to_date():
            self.records.reset_dict()

        base_name = os.path.splitext(name)[0]  # e.g. "IPAT_MuS_Sample1"
        record = self.records.get_record_by_short_id(base_name)
        
        # Cases for existing or new record:
        if record and record.is_in_db and record.all_files_uploaded():
            # A record that is already in the database and fully uploaded
            state = 'append_to_synced'
        elif self.paths.validate_naming_convention(base_name):
            # Matches pattern like 'Institute_UserName_Sample-Name'
            state = 'valid_record_name'
        else:
            # Fails naming convention, needs manual rename
            state = 'invalid_name'

        # Decide next steps using 'match' for clarity
        match state:
            case 'append_to_synced':
                # The record was uploaded to DB, but user may want to append new data
                if self.ui.prompt_append_record(base_name):
                    self.add_item_to_record(record, path, base_name, extension)
                else:
                    # Prompt user for new record name (no "invalid" prompt needed)
                    self.prompt_item_rename(path, name, bad_name_prompt=False, new_record_prompt=True)
            
            case 'valid_record_name':
                # We can attach it directly to the existing record or create a new one if none found
                self.add_item_to_record(record, path, base_name, extension, notify=False)
            
            case 'invalid_name':
                # Prompt user to rename the file/folder
                self.prompt_item_rename(path, name)

    def prompt_item_rename(self, path, name, bad_name_prompt=True, new_record_prompt=False):
        """
        Shows various user prompts (warnings, info dialogs) guiding them to rename
        the file/folder. If user cancels, the file/folder is moved to a "rename" folder
        for further handling.

        :param path: Full path to the original file/folder.
        :param name: The original file/folder name.
        :param bad_name_prompt: If True, show a message about invalid naming convention.
        :param new_record_prompt: If True, show a message about creating a new record name.
        """
        # Optional warning prompt for invalid naming
        if bad_name_prompt:
            message = (
                f"The {'folder' if os.path.isdir(path) else 'file'} '{name}' "
                "does not adhere to the naming convention.\n"
                "Format: Institute_UserName_Sample-Name"
            )
            self.ui.show_warning("Invalid Name", message)
        
        # Optional info prompt for creating a new record
        if new_record_prompt:
            message = (
                f"Please provide the name for your new record\n"
                "Format: Institute_UserName_Sample-Name"
            )
            self.ui.show_info("New Record", message)

        extension = os.path.splitext(name)[1] 

        # Loop until the user either provides a valid name or cancels
        while True:
            dialog_result = self.ui.prompt_rename()  # Returns dict or None
            is_valid, result = self.paths.validate_user_input(dialog_result)
            if not is_valid:
                if result == "User cancelled the dialog.":
                    # Move item to rename folder if user cancels
                    logger.info("User cancelled the dialog.")
                    self.storage.move_to_directory(
                        path,
                        self.paths.get_rename_path(name), 
                        f"Moved '{name}' to rename folder."
                    )
                    self.ui.show_info(
                        "Operation Cancelled", 
                        "The file/folder has been moved to the rename folder."
                    )
                    return
                else:
                    # The user left some fields empty or invalid
                    self.ui.show_warning("Incomplete Information", result)
                    continue

            # If valid, we reconstruct a new name and try to route again
            user_ID, institute, sample_ID = result
            name = f"{institute}_{user_ID}_{sample_ID}{extension}"
            self.route_item_via_name(name, extension, path)
            break

    def add_item_to_record(self, record, path, base_name, extension, notify=True):
        """
        Attaches the file/folder at 'path' to the specified record. If the record
        does not exist yet, this creates a new one. Then moves/renames the file/folder
        and informs the user if 'notify' is True.

        :param record: The LocalRecord object if it exists, or None.
        :param path: The path to the file/folder.
        :param base_name: The base name for the file/folder (e.g. 'IPAT_MuS_Sample1').
        :param extension: The file extension (e.g. '.tif' or '').
        :param notify: If True, display a success message in the UI once moved.
        """
        try:
            # If the record doesn't exist, create a new one
            if not record:
                record_info = self.ids.generate_new_record_info(
                    base_name=base_name, 
                    data_type=self.item_data_type, 
                    record_count=self.records.get_num_records(),
                )
                record = self.records.create_record(record_info)

            # Generate a unique file ID and construct the record directory
            file_id = self.ids.generate_file_id(base_name)
            record_path = self.paths.get_record_path(record)
            os.makedirs(record_path, exist_ok=True)

            # Perform device-specific operations (implemented in subclasses)
            new_file_path = self.device_specific_processing(
                record_path, file_id, path, base_name, extension
            )

            # Optionally inform the user of the successful rename/move
            if notify:
                msg_type = "Folder" if os.path.isdir(path) else "File"
                self.ui.show_info("Success", 
                    f"{msg_type} renamed to '{os.path.basename(new_file_path)}'")

            logger.info(f"{'Folder' if os.path.isdir(path) else 'File'} '{path}' "
                        f"renamed to '{new_file_path}'.")

            # Add this item to the record's list of files and manage session
            self.records.add_item_to_record(new_file_path, record)
            self.session_controller.manage_session()

        except Exception as e:
            # If something fails, inform the user and move the file to exceptions folder
            self.ui.show_error("Error", f"Failed to rename: {e}")
            self.storage.move_to_exception_folder(path)

    def sync_records_to_database(self):
        self.records.sync_records_to_database()

    @abstractmethod
    def device_specific_processing(
        self, record_path, file_id, source_path, base_name, extension
    ):
        """
        A hook for subclasses to implement device-specific or file-type-specific
        file manipulations (e.g., flattening directories, generating metadata).
        This method is expected to return the final path where the item ends up.
        """
        raise NotImplementedError


class SEMFileProcessor(BaseFileProcessor):
    """
    A concrete implementation of the BaseFileProcessor designed to handle
    SEM (Scanning Electron Microscope) data. This handles:
      - TIFF or TIF image files (marked as 'IMG')
      - .elid directories (marked as 'ELID')
    """

    def is_valid_datatype(self, path: str):
        """
        Checks if the path is either a TIFF/TIF file or a directory containing
        .elid files. Returns (True, 'IMG') if it's a TIFF, or (True, 'ELID') if
        an '.elid' file is found in the directory, otherwise (False, None).

        :param path: The path to the file or directory.
        :return: (bool, str or None)
        """
        # If it's a .tif or .tiff, treat it as image data
        if path.lower().endswith(('.tiff', '.tif')):
            return True, 'IMG'
        # If it’s a directory containing .elid files, treat it as ELID data
        elif any(f.endswith('.elid') for f in os.listdir(path)):
            return True, 'ELID'
        # Otherwise, it's not recognized
        return False, None

    def device_specific_processing(
        self, record_path, file_id, source_path, base_name, extension
    ):
        """
        Handles the unique steps for SEM data, namely:
          - Flattening .elid directories before moving them.
          - Moving .tif/.tiff files directly.
        
        :param record_path: Destination directory for the record.
        :param file_id: Generated identifier for the file (e.g., REM_01_IPAT_MuS_SampleID_20231212).
        :param source_path: The original path of the item.
        :param base_name: The base name used for naming logic (e.g. 'IPAT_MuS_Sample1').
        :param extension: The file extension (e.g. '.tif').
        :return: The final path to which the file/folder was moved.
        """
        # If it's ELID data, flatten the directory first
        if self.item_data_type == 'ELID':
            self.flatten_elid_directory(source_path, base_name)
            new_file_path = os.path.join(record_path, file_id)
            # Move the entire directory to the record's folder
            self.storage.move_item(source_path, new_file_path)
            return new_file_path
        else:
            # For images, move the file directly with a unique filename
            new_file_path = self.paths.get_unique_filename(record_path, file_id, extension)
            self.storage.move_item(source_path, new_file_path)
            return new_file_path

    def flatten_elid_directory(self, folder_path: str, base_name: str):
        """
        Traverses the specified folder, moving and renaming .elid/.odt files (and others)
        so that no subdirectories remain. Ensures unique, consistent filenames.

        :param folder_path: The root directory containing .elid files.
        :param base_name: The base name used for renaming .elid/.odt files.
        """
        target_dir = folder_path  # We flatten in place, then move the entire folder later.
        renamed_files = {}

        # Walk in reverse (topdown=False) so we handle files first, then remove dirs
        for root, dirs, files in os.walk(folder_path, topdown=False):
            for fname in files:
                old_path = os.path.join(root, fname)
                new_fname = fname

                # If it's .elid or .odt, rename to incorporate base_name
                if fname.endswith('.elid') or fname.endswith('.odt'):
                    _, ext = os.path.splitext(fname)
                    new_fname = f"{base_name}{ext}"

                # If it's in an analysis directory, prefix the folder name to the file name
                dirname = os.path.basename(root)
                if 'analysis' in dirname and 'analysis' not in fname:
                    new_fname = f"{dirname}-{fname}".replace(' ', '-').replace('_', '-')

                original_new_fname = new_fname
                counter = 1
                # Ensure uniqueness in case of collisions
                while (new_fname in renamed_files or 
                       os.path.exists(os.path.join(target_dir, new_fname))):
                    name_only, ext = os.path.splitext(original_new_fname)
                    new_fname = f"{name_only}_{counter}{ext}"
                    counter += 1

                renamed_files[new_fname] = True
                new_path = os.path.join(target_dir, new_fname)

                try:
                    # Move and rename the file
                    self.storage.move_item(old_path, new_path)
                    logger.info(f"Moved and renamed '{old_path}' to '{new_path}'.")
                except Exception as e:
                    logger.error(f"Failed to move and rename '{old_path}' to '{new_path}': {e}")

            # Remove the now-empty subdirectory
            try:
                os.rmdir(root)
                logger.info(f"Removed empty directory: '{root}'.")
            except OSError:
                logger.warning(f"Directory not empty or removal error: '{root}'.")

        logger.info("All files have been moved and subdirectories eliminated.")
