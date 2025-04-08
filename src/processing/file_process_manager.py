from pathlib import Path

from src.processing.metadata_extractor import MetadataExtractor
from src.processing.file_processor_abstract import BaseFileProcessor
from src.storage.storage_manager import StorageManager
from src.storage.path_manager import PathManager
from src.processing.filename_validator import FilenameValidator
from src.records.id_generator import IdGenerator

from src.records.local_record import LocalRecord
from src.sessions.session_manager import SessionManager
from src.records.record_manager import RecordManager
from src.sync.sync_abstract import ISyncManager
from src.app.logger import setup_logger
from src.ui.ui_abstract import UserInterface
from src.ui.ui_messages import WarningMessages, InfoMessages, ErrorMessages
from src.ui.dialogs import RenameDialog

logger = setup_logger(__name__)


class FileProcessManager:
    def __init__(
        self,
        ui: UserInterface,
        sync_manager: ISyncManager,
        session_manager: SessionManager,
        file_processor: BaseFileProcessor,
    ):
        self.ui = ui
        self.session_manager = session_manager
        self.records = RecordManager(sync_manager=sync_manager)
        self.file_processor = file_processor

        PathManager.init_dirs()

        if not self.records.all_records_uploaded():
            logger.debug("Syncing records to database upon startup.")
            self.sync_records_to_database()

    def process_item(self, src_path: str):
        src_path = self.file_processor.device_specific_preprocessing(src_path)
        filename_prefix, extension = self._parse_filename(src_path)

        if not self.file_processor.is_valid_datatype(src_path):
            self._handle_invalid_datatype(src_path, filename_prefix, extension)
            return

        self._route_item(src_path, filename_prefix, extension)

    def _parse_filename(self, src_path: str) -> tuple[str, str]:
        p = Path(src_path)
        return p.stem, p.suffix

    def _handle_invalid_datatype(
        self, src_path: str, filename_prefix: str, extension: str
    ):
        StorageManager.move_to_exception_folder(src_path, filename_prefix, extension)
        self.ui.show_warning(
            WarningMessages.INVALID_DATA_TYPE, WarningMessages.INVALID_DATA_TYPE_DETAILS
        )
        logger.debug(f"Moved invalid item '{src_path}' to exception folder.")

    def _route_item(self, src_path: str, filename_prefix: str, extension: str):
        sanitized_prefix, is_valid_format = FilenameValidator.sanitize_and_validate(
            filename_prefix
        )
        record_id = IdGenerator.generate_record_id(sanitized_prefix)
        record = self.records.get_record_by_id(record_id)
        state = self._determine_routing_state(
            record, is_valid_format, filename_prefix, extension
        )

        if state == "unappendable_record":
            self._handle_unappendable_record(src_path, sanitized_prefix, extension)
            return

        if state == "append_to_synced":
            self._handle_append_to_synced_record(
                record, src_path, sanitized_prefix, extension
            )
            return

        if state == "valid_name":
            self.add_item_to_record(
                record, src_path, sanitized_prefix, extension, notify=False
            )
            return

        self._prompt_item_rename(src_path, filename_prefix, extension)

    def _determine_routing_state(
        self,
        record: LocalRecord,
        is_valid_format: bool,
        filename_prefix: str,
        extension: str,
    ) -> str:
        if record and not self.file_processor.is_appendable(
            record, filename_prefix, extension
        ):
            return "unappendable_record"
        if record and record.is_in_db and record.all_files_uploaded():
            return "append_to_synced"
        if record or is_valid_format:
            return "valid_name"
        return "invalid_name"

    def _handle_unappendable_record(
        self, src_path: str, filename_prefix: str, extension: str
    ):
        self.ui.show_warning(
            WarningMessages.INVALID_RECORD, WarningMessages.INVALID_RECORD_DETAILS
        )
        self._prompt_item_rename(
            src_path, filename_prefix, extension, bad_name_prompt=False
        )

    def _handle_append_to_synced_record(
        self, record, src_path, filename_prefix, extension
    ):
        if self.ui.prompt_append_record(filename_prefix):
            self.add_item_to_record(record, src_path, filename_prefix, extension)
        else:
            self._prompt_item_rename(
                src_path,
                filename_prefix,
                extension,
                bad_name_prompt=False,
                new_record_prompt=True,
            )

    def _prompt_item_rename(
        self,
        src_path: str,
        filename_prefix: str,
        extension: str,
        bad_name_prompt: bool = True,
        new_record_prompt: bool = False,
    ):
        new_prefix = self._get_valid_rename(
            src_path, filename_prefix, extension, bad_name_prompt, new_record_prompt
        )

        if new_prefix is not None:
            self._route_item(src_path, new_prefix, extension)
            return

        # user canceled or never got a valid rename
        StorageManager.move_to_rename_folder(src_path, filename_prefix, extension)
        self.ui.show_info(
            InfoMessages.OPERATION_CANCELLED, InfoMessages.MOVED_TO_RENAME
        )

    def _get_valid_rename(
        self,
        src_path: str,
        filename_prefix: str,
        extension: str,
        bad_name_prompt: bool,
        new_record_prompt: bool,
        last_attempt: str = None,
    ) -> str | None:
        """
        Asks user for a valid rename, repeatedly if necessary,
        or returns None if user cancels.
        """
        # We'll track the "last analysis" so we can show errors in the dialog each time
        attempted = last_attempt if last_attempt else filename_prefix
        last_analysis = FilenameValidator.explain_filename_violation(attempted)

        while True:
            # Show rename UI to the user, feeding in the last analysis so we can highlight errors
            if bad_name_prompt:
                user_input = self.ui.show_rename_dialog(attempted, last_analysis)
            else:
                user_input = self.ui.prompt_rename()

            # If user canceled, bail out
            if user_input is None:
                return None

            # Now do the real analysis
            analysis = FilenameValidator.analyze_user_input(user_input)

            if analysis["valid"]:
                # It's correct, return sanitized name
                return analysis["sanitized"]
            else:
                # It's invalid. We'll remain in the loop and show the dialog again.
                # Set "attempted" to what the user typed, so they see the same text next time
                attempted = f"{user_input.get('name', '')}-{user_input.get('institute', '')}-{user_input.get('sample_ID', '')}"
                last_analysis = (
                    analysis  # so next iteration highlights the correct errors
                )

    def add_item_to_record(
        self, record, src_path, filename_prefix, extension, notify=True
    ):
        try:
            record = self._get_or_create_record(record, filename_prefix)
            final_path, datatype = self._prepare_final_path(
                src_path, filename_prefix, extension
            )
            record.datatype = datatype

            if notify:
                self._notify_success(src_path, final_path)

            logger.debug(
                f"{'Folder' if Path(src_path).is_dir() else 'File'} '{src_path}' moved/renamed to '{final_path}'."
            )

            self._update_record(final_path, record)
            self._manage_session()

        except Exception as e:
            self.ui.show_error(
                "Error", ErrorMessages.RENAME_FAILED.format(error=str(e))
            )
            StorageManager.move_to_exception_folder(
                src_path, filename_prefix, extension
            )

    def _prepare_final_path(
        self, src_path: str, filename_prefix: str, extension: str
    ) -> tuple[str, str]:
        record_path = PathManager.get_record_path(filename_prefix)
        file_id = IdGenerator.generate_file_id(filename_prefix)
        final_path, datatype = self.file_processor.device_specific_processing(
            src_path, record_path, file_id, extension
        )
        return final_path, datatype

    def _notify_success(self, src_path: str, final_path: str):
        item_type = "Folder" if Path(src_path).is_dir() else "File"
        self.ui.show_info(
            InfoMessages.SUCCESS,
            InfoMessages.ITEM_RENAMED.format(
                item_type=item_type, filename=Path(final_path).name
            ),
        )

    def _update_record(self, final_path: str, record: LocalRecord):
        self.records.add_item_to_record(final_path, record)

    def _manage_session(self):
        if not self.session_manager.session_active:
            self.session_manager.start_session()
            logger.debug("Started a new session.")
        else:
            self.session_manager.reset_timer()
            logger.debug(
                "Session is active. Timer has been reset to extend the session."
            )

    def _get_or_create_record(
        self, record: LocalRecord, filename_prefix: str
    ) -> LocalRecord:
        if record is not None:
            return record
        return self.records.create_record(filename_prefix)

    def sync_records_to_database(self):
        self.records.sync_records_to_database()

    def sync_logs_to_database(self):
        self.records.sync_logs_to_database()
