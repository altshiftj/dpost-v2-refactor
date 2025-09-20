"""Coordinated file ingestion pipeline that hands off to device plugins."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import queue
import re
from typing import Optional, Tuple

from ipat_watchdog.metrics import FILES_FAILED
from ipat_watchdog.core.config import ConfigService, DeviceConfig, get_service
from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.core.processing.error_handling import safe_move_to_exception
from ipat_watchdog.core.processing.models import (
    ProcessingCandidate,
    ProcessingRequest,
    ProcessingResult,
    ProcessingStatus,
    RouteContext,
    RoutingDecision,
)
from ipat_watchdog.core.processing.notifications import notify_success
from ipat_watchdog.core.processing.processor_factory import FileProcessorFactory
from ipat_watchdog.core.processing.record_flow import (
    handle_append_to_synced_record,
    handle_unappendable_record,
)
from ipat_watchdog.core.processing.record_utils import (
    apply_device_defaults,
    get_or_create_record,
    manage_session,
    update_record,
)
from ipat_watchdog.core.processing.rename_flow import RenameService
from ipat_watchdog.core.processing.routing import (
    determine_routing_state,
    fetch_record_for_prefix,
)
from ipat_watchdog.core.processing.stability_tracker import FileStabilityTracker
from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS, ProcessingOutput
from ipat_watchdog.core.records.record_manager import RecordManager
from ipat_watchdog.core.session.session_manager import SessionManager
from ipat_watchdog.core.storage.filesystem_utils import (
    generate_file_id,
    get_record_path,
    move_to_exception_folder,
    parse_filename,
)
from ipat_watchdog.core.sync.sync_abstract import ISyncManager
from ipat_watchdog.core.interactions import UserInteractionPort

logger = setup_logger(__name__)

_INTERNAL_STAGING_SUFFIX_RE = re.compile(
    r'^(?P<prefix>.*?)(?P<marker>\.__staged__(?P<count>\d+)?)(?P<duplicate>\s*\(\d+\))?(?P<extension>(\.[^.]+)*)$',
    re.IGNORECASE,
)


class FileProcessManager:
    """Single-threaded pipeline that validates, routes, and persists artefacts."""

    def __init__(
        self,
        interactions: UserInteractionPort,
        sync_manager: ISyncManager,
        session_manager: SessionManager,
        config_service: ConfigService | None = None,
        file_processor: FileProcessorABS | None = None,
    ) -> None:
        self.interactions = interactions
        self.session_manager = session_manager
        self.config_service = config_service or get_service()
        self.file_processor = file_processor
        self.records = RecordManager(sync_manager=sync_manager)
        self._processor_factory = FileProcessorFactory()
        self._rename_service = RenameService(interactions)
        self._rejected_queue: queue.Queue[Tuple[str, str]] = queue.Queue()

        if not self.records.all_records_uploaded():
            logger.debug("Syncing records to database upon startup")
            self.sync_records_to_database()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def process_item(self, src_path: str) -> ProcessingResult:
        path = Path(src_path)

        if self._is_internal_staging_path(path):
            message = f"Ignoring internal staging path: {path}"
            logger.debug(message)
            return ProcessingResult(ProcessingStatus.DEFERRED, message)

        device = self.config_service.first_matching_device(src_path)
        if device is None:
            return self._reject_immediately(path, "Invalid file type")

        stability_outcome = FileStabilityTracker(path, device).wait()
        if stability_outcome.rejected:
            reason = stability_outcome.reason or "File rejected by stability guard"
            self._register_rejection(str(path), reason)
            safe_move_to_exception(str(path))
            FILES_FAILED.inc()
            return ProcessingResult(ProcessingStatus.REJECTED, reason)

        request = ProcessingRequest(source=path, device=device)
        candidate: Optional[ProcessingCandidate] = None

        try:
            with self.config_service.activate_device(device):
                processor = self._resolve_processor(device)
                item = self._build_candidate(request, processor)
                if isinstance(item, ProcessingResult):
                    return item
                candidate = item
                context = self._build_route_context(candidate)
                return self._dispatch_route(context)
        except Exception as exc:
            self._handle_processing_failure(path, candidate, exc)
            raise RuntimeError(f"File processing failed for {src_path}: {exc}") from exc

    def get_and_clear_rejected(self) -> list[Tuple[str, str]]:
        rejected: list[Tuple[str, str]] = []
        while True:
            try:
                rejected.append(self._rejected_queue.get_nowait())
            except queue.Empty:
                break
        return rejected

    def add_item_to_record(
        self,
        record,
        src_path: str,
        filename_prefix: str,
        extension: str,
        file_processor: Optional[FileProcessorABS] = None,
        notify: bool = True,
        device: DeviceConfig | None = None,
    ) -> Optional[str]:
        processor = file_processor or self.file_processor
        if processor is None:
            move_to_exception_folder(src_path)
            FILES_FAILED.inc()
            raise RuntimeError("No file processor available")

        device = device or self.config_service.current_device()
        record = get_or_create_record(self.records, record, filename_prefix, device)
        device_abbr = device.metadata.device_abbr if device else None
        apply_device_defaults(record, device)

        record_path = get_record_path(filename_prefix, device_abbr)
        file_id = generate_file_id(filename_prefix, device_abbr)
        output: ProcessingOutput = processor.device_specific_processing(
            src_path, record_path, file_id, extension
        )

        record.datatype = output.datatype
        if notify:
            notify_success(self.interactions, src_path, output.final_path)

        logger.debug("Processed %s -> %s", src_path, output.final_path)

        update_record(self.records, output.final_path, record)
        manage_session(self.session_manager, record)

        return output.final_path

    def sync_records_to_database(self) -> None:
        if self.records.all_records_uploaded():
            logger.debug("All records already uploaded, skipping sync")
            return
        logger.debug("Syncing records to database")
        self.records.sync_records_to_database()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _resolve_processor(self, device: DeviceConfig) -> FileProcessorABS:
        if self.file_processor is not None:
            return self.file_processor
        return self._processor_factory.get_for_device(device.identifier)

    def _build_candidate(
        self,
        request: ProcessingRequest,
        processor: FileProcessorABS,
    ) -> ProcessingCandidate | ProcessingResult:
        preprocessed = processor.device_specific_preprocessing(str(request.source))
        if preprocessed is None:
            return ProcessingResult(ProcessingStatus.DEFERRED, "Awaiting paired artefact")

        parse_target = self._strip_internal_stage_suffix(Path(preprocessed))
        prefix, extension = parse_filename(str(parse_target))

        effective_path = Path(preprocessed)
        if not effective_path.exists():
            effective_path = request.source

        preprocessed_path = Path(preprocessed)
        if preprocessed_path == effective_path:
            preprocessed_path = None

        return ProcessingCandidate(
            original_path=request.source,
            effective_path=effective_path,
            prefix=prefix,
            extension=extension,
            processor=processor,
            device=request.device,
            preprocessed_path=preprocessed_path,
        )

    def _build_route_context(self, candidate: ProcessingCandidate) -> RouteContext:
        sanitized_prefix, is_valid_format, record = fetch_record_for_prefix(
            self.records, candidate.prefix, candidate.device
        )
        decision = determine_routing_state(
            record,
            is_valid_format,
            candidate.prefix,
            candidate.extension,
            candidate.processor,
        )
        return RouteContext(candidate, sanitized_prefix, record, decision)

    def _dispatch_route(self, context: RouteContext) -> ProcessingResult:
        candidate = context.candidate

        def rename_delegate(path, prefix, ext, contextual_reason=None):
            return self._invoke_rename_flow(candidate, prefix, ext, contextual_reason)

        if context.decision is RoutingDecision.UNAPPENDABLE:
            return handle_unappendable_record(self.interactions, rename_delegate, context)

        if context.decision is RoutingDecision.APPEND_TO_SYNCED:
            return handle_append_to_synced_record(
                self.interactions,
                lambda *args, **kwargs: self.add_item_to_record(*args, **kwargs, device=candidate.device),
                rename_delegate,
                context,
            )

        if context.decision is RoutingDecision.ACCEPT:
            final_path = self.add_item_to_record(
                context.existing_record,
                str(candidate.effective_path),
                context.sanitized_prefix,
                candidate.extension,
                candidate.processor,
                notify=False,
                device=candidate.device,
            )
            return ProcessingResult(ProcessingStatus.PROCESSED, "Processed item", Path(final_path))

        return self._invoke_rename_flow(
            candidate,
            candidate.prefix,
            candidate.extension,
        )

    def _invoke_rename_flow(
        self,
        candidate: ProcessingCandidate,
        current_prefix: str,
        extension: str,
        contextual_reason: Optional[str] = None,
    ) -> ProcessingResult:
        outcome = self._rename_service.obtain_valid_prefix(current_prefix, contextual_reason)
        if outcome.cancelled or not outcome.sanitized_prefix:
            self._rename_service.send_to_manual_bucket(
                str(candidate.effective_path), current_prefix, extension
            )
            return ProcessingResult(ProcessingStatus.REJECTED, "Rename cancelled by user")

        updated_candidate = replace(candidate, prefix=outcome.sanitized_prefix)
        return self._route_with_prefix(updated_candidate, outcome.sanitized_prefix)

    def _route_with_prefix(
        self, candidate: ProcessingCandidate, prefix_override: str
    ) -> ProcessingResult:
        sanitized_prefix, is_valid_format, record = fetch_record_for_prefix(
            self.records, prefix_override, candidate.device
        )
        decision = determine_routing_state(
            record,
            is_valid_format,
            prefix_override,
            candidate.extension,
            candidate.processor,
        )
        updated = replace(candidate, prefix=prefix_override)
        return self._dispatch_route(RouteContext(updated, sanitized_prefix, record, decision))

    @staticmethod
    def _strip_internal_stage_suffix(path: Path) -> Path:
        name = path.name
        match = _INTERNAL_STAGING_SUFFIX_RE.match(name)
        if not match:
            return path

        prefix = match.group('prefix')
        extension = match.group('extension')
        if not prefix and not extension:
            return path
        return path.with_name(f"{prefix}{extension}")

    @staticmethod
    def _is_internal_staging_path(path: Path) -> bool:
        if _INTERNAL_STAGING_SUFFIX_RE.match(path.name):
            return True
        return any(_INTERNAL_STAGING_SUFFIX_RE.match(parent.name) for parent in path.parents)

    def _reject_immediately(self, path: Path, reason: str) -> ProcessingResult:
        move_to_exception_folder(path)
        self._register_rejection(str(path), reason)
        FILES_FAILED.inc()
        return ProcessingResult(ProcessingStatus.REJECTED, reason)

    def _register_rejection(self, path: str, reason: str) -> None:
        logger.warning("Rejected %s: %s", path, reason)
        self._rejected_queue.put((path, reason))

    def _handle_processing_failure(
        self,
        path: Path,
        candidate: Optional[ProcessingCandidate],
        exc: Exception,
    ) -> None:
        logger.exception("Error processing %s: %s", path, exc)
        target = str(candidate.effective_path) if candidate else str(path)
        prefix = candidate.prefix if candidate else path.stem
        extension = candidate.extension if candidate else path.suffix
        safe_move_to_exception(target, prefix, extension)
        if candidate and candidate.preprocessed_path and candidate.preprocessed_path != candidate.effective_path:
            safe_move_to_exception(str(candidate.preprocessed_path), prefix, extension)
        self._register_rejection(str(path), str(exc))
        FILES_FAILED.inc()

