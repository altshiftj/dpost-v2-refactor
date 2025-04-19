from pathlib import Path

from ipat_watchdog.__main__ import FILES_FAILED
from ipat_watchdog.processing.metadata_extractor import MetadataExtractor
from ipat_watchdog.processing.file_processor_abstract import FileProcessorABS
from ipat_watchdog.storage.filesystem_utils import (
    parse_filename,
    move_to_exception_folder,
    move_to_rename_folder,
    get_record_path,
    generate_record_id,
    generate_file_id,
    sanitize_and_validate,
    explain_filename_violation,
    analyze_user_input,
)
from ipat_watchdog.records.local_record import LocalRecord
from ipat_watchdog.sessions.session_manager import SessionManager
from ipat_watchdog.records.record_manager import RecordManager
from ipat_watchdog.sync.sync_abstract import ISyncManager
from ipat_watchdog.app.logger import setup_logger
from ipat_watchdog.ui.ui_abstract import UserInterface
from ipat_watchdog.ui.ui_messages import WarningMessages, InfoMessages, ErrorMessages, DialogPrompts

logger = setup_logger(__name__)

UNAPPENDABLE = "unappendable_record"
APPEND_SYNCED = "append_to_synced"
VALID_NAME = "valid_name"
INVALID_NAME = "invalid_name"


class FileProcessManager:
    def __init__(
        self,
        ui: UserInterface,
        sync_manager: ISyncManager,
        session_manager: SessionManager,
        file_processor: FileProcessorABS,
    ):
        self.ui = ui
        self.session_manager = session_manager
        self.records = RecordManager(sync_manager=sync_manager)
        self.file_processor = file_processor

        if not self.records.all_records_uploaded():
            logger.debug("Syncing records to database upon startup.")
            self.sync_records_to_database()

    def process_item(self, src_path: str):
        src_path = self.file_processor.device_specific_preprocessing(src_path)
        filename_prefix, extension = parse_filename(src_path)

        if not self.file_processor.is_valid_datatype(src_path):
            self._handle_invalid_datatype(src_path, filename_prefix, extension)
            FILES_FAILED.inc()
            return

        try:
            self._route_item(src_path, filename_prefix, extension)
        except Exception as e:
            logger.exception(f"Error while routing item: {e}")
            self._move_to_exception_and_inform(
                src_path,
                filename_prefix,
                extension,
                severity=ErrorMessages.PROCESSING_ERROR,
                message=ErrorMessages.PROCESSING_ERROR_DETAILS.format(
                    filename=Path(src_path).name, error=str(e)
                ),
            )

    def _move_to_exception_and_inform(
        self, src_path: str, prefix: str, extension: str, severity: str, message: str
    ):
        move_to_exception_folder(src_path, prefix, extension)
        if severity.lower() == "warning":
            self.ui.show_warning(severity, message)
        else:
            self.ui.show_error(severity, message)

        logger.debug(f"Moved item '{src_path}' to exception folder with severity '{severity}'.")

    def _handle_invalid_datatype(self, src_path: str, filename_prefix: str, extension: str):
        self._move_to_exception_and_inform(
            src_path,
            filename_prefix,
            extension,
            severity="Warning",
            message=WarningMessages.INVALID_DATA_TYPE_DETAILS,
        )
        logger.debug(f"Moved invalid item '{src_path}' to exception folder.")

    def _route_item(self, src_path: str, filename_prefix: str, extension: str):
        sanitized_prefix, is_valid_format, record = self._fetch_record_for_prefix(filename_prefix)
        state = self._determine_routing_state(record, is_valid_format, filename_prefix, extension)

        if state == UNAPPENDABLE:
            self._handle_unappendable_record(src_path, sanitized_prefix, extension)
        elif state == APPEND_SYNCED:
            self._handle_append_to_synced_record(record, src_path, sanitized_prefix, extension)
        elif state == VALID_NAME:
            self.add_item_to_record(record, src_path, sanitized_prefix, extension, notify=False)
        else:
            self._rename_flow_controller(src_path, filename_prefix, extension)

    def _fetch_record_for_prefix(self, filename_prefix: str) -> tuple[str, bool, LocalRecord]:
        sanitized_prefix, is_valid_format = sanitize_and_validate(filename_prefix)
        record_id = generate_record_id(sanitized_prefix)
        record = self.records.get_record_by_id(record_id)
        return sanitized_prefix, is_valid_format, record

    def _determine_routing_state(
        self, record: LocalRecord, is_valid_format: bool, filename_prefix: str, extension: str
    ) -> str:
        if record and not self.file_processor.is_appendable(record, filename_prefix, extension):
            return UNAPPENDABLE
        if record and record.is_in_db and record.all_files_uploaded():
            return APPEND_SYNCED
        if record or is_valid_format:
            return VALID_NAME
        return INVALID_NAME

    def _handle_unappendable_record(self, src_path: str, filename_prefix: str, extension: str):
        self.ui.show_warning(
            WarningMessages.INVALID_RECORD, WarningMessages.INVALID_RECORD_DETAILS
        )
        self._rename_flow_controller(
            src_path,
            filename_prefix,
            extension,
            contextual_reason=DialogPrompts.UNAPPENDABLE_RECORD_CONTEXT.format(
                record_id=filename_prefix
            ),
        )

    def _handle_append_to_synced_record(self, record, src_path, filename_prefix, extension):
        if self.ui.prompt_append_record(filename_prefix):
            self.add_item_to_record(record, src_path, filename_prefix, extension)
        else:
            self._rename_flow_controller(
                src_path,
                filename_prefix,
                extension,
                contextual_reason=DialogPrompts.APPEND_RECORD_CANCEL_CONTEXT.format(
                    record_id=filename_prefix
                ),
            )

    def _rename_flow_controller(
        self,
        src_path: str,
        filename_prefix: str,
        extension: str,
        contextual_reason: str = None,
    ):
        new_prefix = self._interactive_rename_loop(
            filename_prefix, last_attempt=None, contextual_reason=contextual_reason
        )

        if new_prefix is not None:
            self._route_item(src_path, new_prefix, extension)
            return

        move_to_rename_folder(src_path, filename_prefix, extension)
        self.ui.show_info(
            InfoMessages.OPERATION_CANCELLED, InfoMessages.MOVED_TO_RENAME
        )

    def _interactive_rename_loop(
        self,
        filename_prefix: str,
        last_attempt: str = None,
        contextual_reason: str = None,
    ) -> str | None:
        attempted = last_attempt if last_attempt else filename_prefix
        last_analysis = explain_filename_violation(attempted)

        if contextual_reason:
            last_analysis["reasons"].insert(0, contextual_reason)

        while True:
            user_input = self.ui.show_rename_dialog(attempted, last_analysis)
            if user_input is None:
                return None

            analysis = analyze_user_input(user_input)
            if analysis["valid"]:
                return analysis["sanitized"]
            else:
                attempted = f"{user_input.get('name', '')}-{user_input.get('institute', '')}-{user_input.get('sample_ID', '')}"
                last_analysis = analysis

    def add_item_to_record(self, record, src_path, filename_prefix, extension, notify=True):
        try:
            record = self._get_or_create_record(record, filename_prefix)

            record_path = get_record_path(filename_prefix)
            file_id = generate_file_id(filename_prefix)
            final_path, datatype = self.file_processor.device_specific_processing(
                src_path, record_path, file_id, extension
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
            self.ui.show_error("Error", ErrorMessages.RENAME_FAILED.format(error=str(e)))
            self._move_to_exception_and_inform(
                src_path,
                filename_prefix,
                extension,
                severity="Error",
                message="Failed to rename.",
            )

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
            logger.debug("Session is active. Timer reset.")

    def _get_or_create_record(self, record: LocalRecord, filename_prefix: str) -> LocalRecord:
        return record if record else self.records.create_record(filename_prefix)

    def sync_records_to_database(self):
        self.records.sync_records_to_database()

    def sync_logs_to_database(self):
        self.records.sync_logs_to_database()
