from pathlib import Path

from src.processing.metadata_extractor import MetadataExtractor
from src.processing.file_processor_abstract import BaseFileProcessor
from src.storage.storage_manager import StorageManager
from src.storage.path_manager import PathManager
from src.utils.filename_validator import FilenameValidator
from src.records.id_generator import IdGenerator

from src.records.local_record import LocalRecord
from src.sessions.session_manager import SessionManager
from src.records.record_manager import RecordManager
from src.sync.sync_abstract import ISyncManager
from src.app.logger import setup_logger
from src.ui.ui_abstract import UserInterface
from src.ui.ui_messages import WarningMessages, InfoMessages, ErrorMessages

logger = setup_logger(__name__)

class FileProcessManager:
    """
    Coordinates the overall workflow for new or updated files/folders within the
    data-watchdog system. This class acts as the primary entry point for file events:
    it validates file types via the configured BaseFileProcessor, manages user prompts
    (e.g., renaming and record decisions), handles session control, and updates or
    creates records accordingly. If a file does not meet criteria or the user opts out,
    it routes items to rename or exception folders. The FileProcessManager also ensures
    pending records are synchronized to the database on startup and after processing.
    """

    def __init__(
        self,
        ui:                 UserInterface,
        sync_manager:       ISyncManager,
        session_manager:    SessionManager,
        file_processor:     'BaseFileProcessor',
    ):
        self.ui                 = ui
        self.session_manager    = session_manager
        self.records            = RecordManager(sync_manager=sync_manager)
        self.file_processor:    BaseFileProcessor = file_processor

        # initialize directories
        PathManager.init_dirs()

        # If any record is not fully uploaded, sync on startup
        if not self.records.all_records_uploaded():
            logger.debug("Syncing records to database upon startup.")
            self.sync_records_to_database()

    def process_item(self, src_path: str):
        """
        Entry point when a file/folder is created or modified.
        """
        src_path = self.file_processor.device_specific_preprocessing(src_path)
        filename_prefix, extension = self._parse_filename(src_path)

        valid_datatype = self.file_processor.is_valid_datatype(src_path)
        if not valid_datatype:
            self._handle_invalid_datatype(src_path, filename_prefix, extension)
            return

        # Route item based on record name & state
        self._route_item(src_path, filename_prefix, extension)

    def _parse_filename(self, src_path: str) -> tuple[str, str]:
        """
        Parses the filename from the given src_path and returns a tuple:
        (filename_prefix, extension). Uses pathlib for reliable cross-platform behavior.
        """
        p = Path(src_path)
        return p.stem, p.suffix

    def _handle_invalid_datatype(self, src_path: str, filename_prefix: str, extension: str):
        """
        Moves invalid items to exception folder and informs the user.
        """
        StorageManager.move_to_exception_folder(src_path, filename_prefix, extension)

        self.ui.show_warning(
            WarningMessages.INVALID_DATA_TYPE,
            WarningMessages.INVALID_DATA_TYPE_DETAILS
        )
        logger.debug(f"Moved invalid item '{src_path}' to exception folder.")

    def _route_item(self, src_path: str, filename_prefix: str, extension: str):
        # Sanitize the filename and check validity.
        sanitized_prefix, is_valid_format = FilenameValidator.sanitize_and_validate(filename_prefix)
        record_id = IdGenerator.generate_record_id(sanitized_prefix)
        record = self.records.get_record_by_id(record_id)
        state = self._determine_routing_state(record, is_valid_format, filename_prefix, extension)

        if state == 'unappendable_record':
            self._handle_unappendable_record(src_path, sanitized_prefix, extension)
            return

        if state == 'append_to_synced':
            self._handle_append_to_synced_record(record, src_path, sanitized_prefix, extension)
            return

        if state == 'valid_name':
            self.add_item_to_record(record, src_path, sanitized_prefix, extension, notify=False)
            return

        # invalid_name fallback
        self._prompt_item_rename(src_path, filename_prefix, extension)

    def _determine_routing_state(self, record: LocalRecord, is_valid_format: bool, filename_prefix: str, extension: str) -> str:
        if record and not self.file_processor.is_appendable(record, filename_prefix, extension):
            return 'unappendable_record'

        if record and record.is_in_db and record.all_files_uploaded():
            return 'append_to_synced'

        if record or is_valid_format:
            return 'valid_name'

        return 'invalid_name'

    def _handle_unappendable_record(self, src_path: str, filename_prefix: str, extension: str):
        """
        If the existing record is unappendable, prompt to rename and create a new record.
        """
        self.ui.show_warning(
            WarningMessages.INVALID_RECORD,
            WarningMessages.INVALID_RECORD_DETAILS
        )
        self._prompt_item_rename(src_path, filename_prefix, extension, bad_name_prompt=False)

    def _handle_append_to_synced_record(self, record, src_path, filename_prefix, extension):
        """
        If the record is synced but user may still want to append new data.
        """
        if self.ui.prompt_append_record(filename_prefix):
            self.add_item_to_record(record, src_path, filename_prefix, extension)
        else:
            self._prompt_item_rename(src_path, filename_prefix, extension, bad_name_prompt=False, new_record_prompt=True)


    def _get_valid_rename(self, src_path: str, filename_prefix: str, extension: str,
                          bad_name_prompt: bool, new_record_prompt: bool) -> str | None:
        """
        Prompts the user repeatedly until valid rename data is provided or cancellation.
        Returns the validated new filename prefix or None if the user cancels.
        """
        if bad_name_prompt:
            self.ui.show_warning(
                WarningMessages.INVALID_NAME,
                WarningMessages.INVALID_NAME_DETAILS.format(filename=filename_prefix, extension=extension)
            )
        if new_record_prompt:
            self.ui.show_info(
                InfoMessages.NEW_RECORD,
                InfoMessages.NEW_RECORD_DETAILS
            )
        while True:
            user_input = self.ui.prompt_rename()  # Returns a dict or None
            result, is_valid = FilenameValidator.from_user_input(user_input)

            if is_valid:
                return result

            if result == "User cancelled the dialog.":
                return None
            elif result == "Invalid Parts":
                self.ui.show_warning(
                    WarningMessages.INVALID_CHARACTERS,
                    WarningMessages.INVALID_CHARACTERS_DETAILS
                )
            else:
                self.ui.show_warning(
                    WarningMessages.INCOMPLETE_INFO,
                    WarningMessages.INCOMPLETE_INFO_DETAILS
                )


    def _prompt_item_rename(self, src_path: str, filename_prefix: str, extension: str,
                            bad_name_prompt: bool = True, new_record_prompt: bool = False):
        """
        Simplified method to guide the user to rename the item properly.
        It uses _get_valid_rename to repeatedly prompt the user until valid input is provided.
        If the user cancels, the item is moved to the rename folder.
        """
        new_prefix = self._get_valid_rename(src_path, filename_prefix, extension,
                                            bad_name_prompt, new_record_prompt)
        
        if new_prefix is not None:
            self._route_item(src_path, new_prefix, extension)
            return

        StorageManager.move_to_rename_folder(src_path, filename_prefix, extension)
        self.ui.show_info(
            InfoMessages.OPERATION_CANCELLED, 
            InfoMessages.MOVED_TO_RENAME
            )


    def add_item_to_record(self, record, src_path, filename_prefix, extension, notify=True):
        """
        Attaches the file/folder to an existing or new record, then handles final storage.
        This method has been refactored to delegate:
        1. Final path preparation (_prepare_final_path)
        2. User notification (_notify_success)
        3. Record update (_update_record)
        4. Session management (_manage_session)
        """
        try:
            # 1) Get or create the record.
            record = self._get_or_create_record(record, filename_prefix)
            
            # 2) Prepare final file path and retrieve datatype.
            final_path, datatype = self._prepare_final_path(src_path, filename_prefix, extension)
            record.datatype = datatype
            
            # 3) Notify the user of success, if requested.
            if notify:
                self._notify_success(src_path, final_path)
            
            logger.debug(f"{'Folder' if Path(src_path).is_dir() else 'File'} '{src_path}' moved/renamed to '{final_path}'.")
            
            # 4) Update the record with the new item.
            self._update_record(final_path, record)
            
            # 5) Manage the session (start or reset).
            self._manage_session()
            
        except Exception as e:
            self.ui.show_error(
                "Error", 
                ErrorMessages.RENAME_FAILED.format(error=str(e))
                )
            
            StorageManager.move_to_exception_folder(src_path, filename_prefix, extension)


    def _prepare_final_path(self, src_path: str, filename_prefix: str, extension: str) -> tuple[str, str]:
        """
        Prepares the final storage path for the item.
        - Retrieves the record-specific directory.
        - Generates a unique file ID.
        - Delegates to the device-specific processing for any custom operations.
        Returns the final file path and the datatype.
        """
        record_path = PathManager.get_record_path(filename_prefix)
        file_id = IdGenerator.generate_file_id(filename_prefix)
        final_path, datatype = self.file_processor.device_specific_processing(src_path, record_path, file_id, extension)
        return final_path, datatype


    def _notify_success(self, src_path: str, final_path: str):
        """
        Notifies the user of a successful move/rename.
        Determines the type (Folder/File) and shows an info message.
        """
        item_type = "Folder" if Path(src_path).is_dir() else "File"
        self.ui.show_info(
            InfoMessages.SUCCESS,
            InfoMessages.ITEM_RENAMED.format(item_type=item_type, filename=Path(final_path).name)
        )


    def _update_record(self, final_path: str, record: LocalRecord):
        """
        Adds the processed item to the record.
        """
        self.records.add_item_to_record(final_path, record)


    def _manage_session(self):
        """
        Manages the session: if no session is active, starts a new one; otherwise,
        resets the session timer.
        """
        if not self.session_manager.session_active:
            self.session_manager.start_session()
            logger.debug("Started a new session.")
        else:
            self.session_manager.reset_timer()
            logger.debug("Session is active. Timer has been reset to extend the session.")

    def _get_or_create_record(self, record: LocalRecord, filename_prefix: str) -> LocalRecord:
        """
        Returns an existing record or creates a new one if `record` is None.
        """
        if record is not None:
            return record
        return self.records.create_record(filename_prefix)

    def sync_records_to_database(self):
        """
        Syncs the in-memory records to the external database.
        """
        self.records.sync_records_to_database()

    def sync_logs_to_database(self):
        """
        Syncs the log file to the external database.
        """
        self.records.sync_logs_to_database()
