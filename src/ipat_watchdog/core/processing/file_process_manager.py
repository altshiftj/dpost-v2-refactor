"""Coordinated file ingestion pipeline that hands off to device plugins."""
from __future__ import annotations

import queue
import re
from dataclasses import replace
from pathlib import Path
from typing import Optional, Tuple

from ipat_watchdog.core.config import ConfigService, DeviceConfig, get_service
from ipat_watchdog.core.interactions import UserInteractionPort
from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.core.processing.device_resolver import DeviceResolver
from ipat_watchdog.core.processing.error_handling import safe_move_to_exception
from ipat_watchdog.core.processing.file_processor_abstract import (
    FileProcessorABS, ProcessingOutput)
from ipat_watchdog.core.processing.models import (ProcessingCandidate,
                                                  ProcessingRequest,
                                                  ProcessingResult,
                                                  ProcessingStatus,
                                                  RouteContext,
                                                  RoutingDecision)
from ipat_watchdog.core.processing.notifications import notify_success
from ipat_watchdog.core.processing.processor_factory import \
    FileProcessorFactory
from ipat_watchdog.core.processing.record_flow import \
    handle_unappendable_record
from ipat_watchdog.core.processing.record_utils import (apply_device_defaults,
                                                        get_or_create_record,
                                                        manage_session,
                                                        update_record)
from ipat_watchdog.core.processing.rename_flow import RenameService
from ipat_watchdog.core.processing.routing import (determine_routing_state,
                                                   fetch_record_for_prefix)
from ipat_watchdog.core.processing.stability_tracker import \
    FileStabilityTracker
from ipat_watchdog.core.records.record_manager import RecordManager
from ipat_watchdog.core.session.session_manager import SessionManager
from ipat_watchdog.core.storage.filesystem_utils import (
    generate_file_id, get_record_path, move_to_exception_folder,
    parse_filename)
from ipat_watchdog.core.sync.sync_abstract import ISyncManager
from ipat_watchdog.metrics import FILES_FAILED, FILES_PROCESSED

logger = setup_logger(__name__)

# Recognises artefacts parked in our hidden staging folders (created during preprocessing retries).
_INTERNAL_STAGING_SUFFIX_RE = re.compile(
    r'\.__staged__(\d+)?',
    re.IGNORECASE,
)


class _ProcessingPipeline:
    """Internal helper that orchestrates the multi-stage processing pipeline."""

    def __init__(self, manager: 'FileProcessManager') -> None:
        self._manager = manager

    def process(self, src_path: Path) -> ProcessingResult:
        # Stage 1: resolve a device and wait for stability; may return early with a ProcessingResult.
        prepared = self._prepare_request(src_path)
        if isinstance(prepared, ProcessingResult):
            return prepared
        return self._execute_pipeline(prepared)

    def _prepare_request(self, path: Path) -> ProcessingRequest | ProcessingResult:
        manager = self._manager

        if manager._is_internal_staging_path(path):
            message = f"Ignoring internal staging path: {path}"
            logger.debug(message)
            return ProcessingResult(ProcessingStatus.DEFERRED, message)

        # Device resolver combines selector rules with lightweight processor probes.
        resolution = manager._device_resolver.resolve(path)
        device = resolution.selected
        if device is None:
            reason = resolution.reason or "Invalid file type"
            if resolution.deferred:
                logger.debug("Processing deferred for %s: %s", path, reason)
                return ProcessingResult(ProcessingStatus.DEFERRED, reason)
            return self._reject_immediately(path, reason)
        
        # Block until the artefact stops changing (device overrides can tweak thresholds).
        stability_outcome = FileStabilityTracker(path, device).wait()
        if stability_outcome.rejected:
            reason = stability_outcome.reason or "File rejected by stability guard"
            manager._register_rejection(str(path), reason)
            safe_move_to_exception(str(path))
            FILES_FAILED.inc()
            return ProcessingResult(ProcessingStatus.REJECTED, reason)

        return ProcessingRequest(source=path, device=device)

    def _execute_pipeline(self, request: ProcessingRequest) -> ProcessingResult:
        manager = self._manager
        candidate: Optional[ProcessingCandidate] = None
        try:
            with manager.config_service.activate_device(request.device):
                # Ensure downstream helpers read the selected device's configuration.
                processor = manager._resolve_processor(request.device)
                item = self._build_candidate(request, processor)
                if isinstance(item, ProcessingResult):
                    return item
                candidate = item
                context = self._build_route_context(candidate)
                return self._dispatch_route(context)
        except Exception as exc:
            manager._handle_processing_failure(request.source, candidate, exc)
            raise RuntimeError(f"File processing failed for {request.source}: {exc}") from exc
        # This point should be unreachable because control flow either returns or raises above.
        raise RuntimeError("Unreachable code in _execute_pipeline")

    def _build_candidate(self, request: ProcessingRequest, processor: FileProcessorABS) -> ProcessingCandidate | ProcessingResult:
        manager = self._manager
        preprocessed = processor.device_specific_preprocessing(str(request.source))
        if preprocessed is None:
            return ProcessingResult(ProcessingStatus.DEFERRED, "Awaiting paired artefacts")
        assert preprocessed is not None  # type narrowing for Pylance

        # Normalise any internal staging suffix before deriving prefix/extension.
        parse_target = manager._strip_internal_stage_suffix(Path(preprocessed))
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
        manager = self._manager
        sanitized_prefix, is_valid_format, record = fetch_record_for_prefix(
            manager.records, candidate.prefix, candidate.device
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
        manager = self._manager
        candidate = context.candidate

        def rename_delegate(path, prefix, ext, contextual_reason=None):
            return self._invoke_rename_flow(candidate, prefix, ext, contextual_reason)

        if context.decision is RoutingDecision.UNAPPENDABLE:
            return handle_unappendable_record(manager.interactions, rename_delegate, context)

        # APPEND_TO_SYNCED collapsed into ACCEPT path (automatic append)

        if context.decision is RoutingDecision.ACCEPT:
            final_path = manager.add_item_to_record(
                context.existing_record,
                str(candidate.effective_path),
                context.sanitized_prefix,
                candidate.extension,
                candidate.processor,
                notify=False,
                device=candidate.device,
            )
            if final_path is None:
                return ProcessingResult(ProcessingStatus.PROCESSED, "Processed item")
            return ProcessingResult(ProcessingStatus.PROCESSED, "Processed item", Path(final_path))

        # Remaining cases fall back to the rename flow (invalid format, collisions, etc.).
        return self._invoke_rename_flow(candidate, candidate.prefix, candidate.extension)

    def _invoke_rename_flow(
        self,
        candidate: ProcessingCandidate,
        current_prefix: str,
        extension: str,
        contextual_reason: Optional[str] = None,
    ) -> ProcessingResult:
        manager = self._manager
        # UI-driven rename can either supply a sanitized prefix or bail out to manual processing.
        outcome = manager._rename_service.obtain_valid_prefix(current_prefix, contextual_reason)
        if outcome.cancelled or not outcome.sanitized_prefix:
            manager._rename_service.send_to_manual_bucket(
                str(candidate.effective_path), current_prefix, extension
            )
            FILES_FAILED.inc()
            return ProcessingResult(ProcessingStatus.REJECTED, "Rename cancelled by user")

        updated_candidate = replace(candidate, prefix=outcome.sanitized_prefix)
        return self._route_with_prefix(updated_candidate, outcome.sanitized_prefix)

    def _route_with_prefix(self, candidate: ProcessingCandidate, prefix_override: str) -> ProcessingResult:
        manager = self._manager
        sanitized_prefix, is_valid_format, record = fetch_record_for_prefix(
            manager.records, prefix_override, candidate.device
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

    def _reject_immediately(self, path: Path, reason: str) -> ProcessingResult:
        manager = self._manager
        if manager._is_internal_staging_path(path):
            logger.info("Internal staging folder ignored: %s", path)
            manager._register_rejection(str(path), reason)
            return ProcessingResult(ProcessingStatus.DEFERRED, reason)
        move_to_exception_folder(str(path))
        manager._register_rejection(str(path), reason)
        FILES_FAILED.inc()
        return ProcessingResult(ProcessingStatus.REJECTED, reason)


class FileProcessManager:
    """Single-threaded pipeline that validates, routes, and persists artefacts.

    immediate_sync: if True, attempt to sync records to the database after each
    successfully processed item. This bypasses the previous end-of-session
    batching strategy.
    """

    def __init__(
        self,
        interactions: UserInteractionPort,
        sync_manager: ISyncManager,
        session_manager: SessionManager,
        config_service: ConfigService | None = None,
        file_processor: FileProcessorABS | None = None,
        immediate_sync: bool = False,
    ) -> None:
        self.interactions = interactions
        self.session_manager = session_manager
        self.config_service = config_service or get_service()
        self.file_processor = file_processor
        self.records = RecordManager(sync_manager=sync_manager)
        self._processor_factory = FileProcessorFactory()
        self._device_resolver = DeviceResolver(self.config_service, self._processor_factory)
        self._rename_service = RenameService(interactions)
        self._rejected_queue: queue.Queue[Tuple[str, str]] = queue.Queue()
        self._pipeline = _ProcessingPipeline(self)
        self._immediate_sync = immediate_sync

        if not self.records.all_records_uploaded():
            logger.debug("Syncing records to database upon startup")
            self.sync_records_to_database()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def process_item(self, src_path: str) -> ProcessingResult:
        return self._pipeline.process(Path(src_path))

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

        new_files = update_record(self.records, output.final_path, record)
        if new_files > 0:
            FILES_PROCESSED.inc(new_files)

        # Immediate sync path (best-effort) — keeps prior startup sync logic.
        if self._immediate_sync:
            try:
                if not self.records.all_records_uploaded():
                    self.records.sync_records_to_database()
            except Exception as exc:  # noqa: BLE001
                logger.exception("Immediate sync failed after processing %s: %s", src_path, exc)

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
        # Fall back to loading a processor via the factory based on the resolved device.
        # The factory caches instances per device, so repeated calls are inexpensive.
        return self._processor_factory.get_for_device(device.identifier)
    @staticmethod
    def _strip_internal_stage_suffix(path: Path) -> Path:
        name = path.name
        if not _INTERNAL_STAGING_SUFFIX_RE.search(name):
            return path
        # Remove internal staging marker from the filename (e.g., "file.__staged__2.csv" -> "file.csv").
        new_name = _INTERNAL_STAGING_SUFFIX_RE.sub('', name)
        return path.with_name(new_name)

    @staticmethod
    def _is_internal_staging_path(path: Path) -> bool:
        if _INTERNAL_STAGING_SUFFIX_RE.search(path.name):
            return True
        return any(_INTERNAL_STAGING_SUFFIX_RE.search(parent.name) for parent in path.parents)

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
        # Move whichever artefact exists (raw or preprocessed) so nothing lingers in watch folders.
        safe_move_to_exception(target, prefix, extension)
        if candidate and candidate.preprocessed_path and candidate.preprocessed_path != candidate.effective_path:
            safe_move_to_exception(str(candidate.preprocessed_path), prefix, extension)
        self._register_rejection(str(path), str(exc))
        FILES_FAILED.inc()


