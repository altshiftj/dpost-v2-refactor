"""Coordinated file ingestion pipeline that hands off to device plugins."""
from __future__ import annotations

import queue
import re
from dataclasses import replace
from pathlib import Path
from typing import Optional, Tuple

from ipat_watchdog.core.config import ConfigService, DeviceConfig, get_service
from ipat_watchdog.core.interactions import (DialogPrompts, UserInteractionPort,
                                             WarningMessages)
from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.core.processing.device_resolver import DeviceResolver
from ipat_watchdog.core.processing.error_handling import safe_move_to_exception
from ipat_watchdog.core.processing.file_processor_abstract import (
    FileProcessorABS,
    PreprocessingResult,
    ProcessingOutput,
)
from ipat_watchdog.core.processing.modified_event_gate import ModifiedEventGate
from ipat_watchdog.core.processing.models import (ProcessingCandidate,
                                                  ProcessingRequest,
                                                  ProcessingResult,
                                                  ProcessingStatus,
                                                  RouteContext,
                                                  RoutingDecision)
from ipat_watchdog.core.processing.processor_factory import \
    FileProcessorFactory
from ipat_watchdog.core.processing.record_flow import \
    handle_unappendable_record
from ipat_watchdog.core.processing.record_utils import (apply_device_defaults,
                                                        get_or_create_record,
                                                        update_record)
from ipat_watchdog.core.processing.rename_flow import RenameService
from ipat_watchdog.core.processing.routing import (determine_routing_state,
                                                   fetch_record_for_prefix)
from ipat_watchdog.core.processing.stability_tracker import \
    FileStabilityTracker
from ipat_watchdog.core.records.local_record import LocalRecord
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
        # Stage 1: resolve a device; may return early with a ProcessingResult.
        resolved = self._resolve_device_stage(src_path)
        if isinstance(resolved, ProcessingResult):
            return resolved
        # Stage 2: wait for artifact stability before entering preprocessing/routing.
        prepared = self._stabilize_artifact_stage(resolved)
        if isinstance(prepared, ProcessingResult):
            return prepared
        return self._execute_pipeline(prepared)

    def _prepare_request(self, path: Path) -> ProcessingRequest | ProcessingResult:
        """Backward-compatible helper retained while stage extraction is in progress."""
        resolved = self._resolve_device_stage(path)
        if isinstance(resolved, ProcessingResult):
            return resolved
        return self._stabilize_artifact_stage(resolved)

    def _resolve_device_stage(self, path: Path) -> ProcessingRequest | ProcessingResult:
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
                return ProcessingResult(
                    ProcessingStatus.DEFERRED,
                    reason,
                    retry_delay=resolution.retry_delay,
                )
            return self._reject_immediately(path, reason)
        return ProcessingRequest(source=path, device=device)

    def _stabilize_artifact_stage(
        self,
        request: ProcessingRequest,
    ) -> ProcessingRequest | ProcessingResult:
        manager = self._manager
        # Block until the artefact stops changing (device overrides can tweak thresholds).
        stability_outcome = FileStabilityTracker(request.source, request.device).wait()
        if stability_outcome.rejected:
            reason = stability_outcome.reason or "File rejected by stability guard"
            manager._register_rejection(str(request.source), reason)
            safe_move_to_exception(str(request.source))
            FILES_FAILED.inc()
            return ProcessingResult(ProcessingStatus.REJECTED, reason)
        return request

    def _execute_pipeline(self, request: ProcessingRequest) -> ProcessingResult:
        manager = self._manager
        candidate: Optional[ProcessingCandidate] = None
        try:
            with manager.config_service.activate_device(request.device):
                # Ensure downstream helpers read the selected device's configuration.
                processor = manager._resolve_processor(request.device)
                item = self._preprocess_stage(request, processor)
                if isinstance(item, ProcessingResult):
                    return item
                candidate = item
                context = self._route_decision_stage(candidate)
                return self._dispatch_route(context)
        except Exception as exc:
            manager._handle_processing_failure(request.source, candidate, exc)
            raise RuntimeError(f"File processing failed for {request.source}: {exc}") from exc
        # This point should be unreachable because control flow either returns or raises above.
        raise RuntimeError("Unreachable code in _execute_pipeline")

    def _preprocess_stage(
        self,
        request: ProcessingRequest,
        processor: FileProcessorABS,
    ) -> ProcessingCandidate | ProcessingResult:
        """Run preprocessing and return a routable candidate or deferred result."""
        return self._build_candidate(request, processor)

    def _build_candidate(self, request: ProcessingRequest, processor: FileProcessorABS) -> ProcessingCandidate | ProcessingResult:
        preprocessed = processor.device_specific_preprocessing(str(request.source))
        if preprocessed is None:
            return ProcessingResult(ProcessingStatus.DEFERRED, "Awaiting paired artefacts")
        assert isinstance(preprocessed, PreprocessingResult)  # type narrowing for Pylance

        prefix, extension, effective_path, preprocessed_path = self._derive_candidate_metadata(
            request, preprocessed
        )

        return ProcessingCandidate(
            original_path=request.source,
            effective_path=effective_path,
            prefix=prefix,
            extension=extension,
            processor=processor,
            device=request.device,
            preprocessed_path=preprocessed_path,
        )

    def _derive_candidate_metadata(
        self,
        request: ProcessingRequest,
        preprocessed: PreprocessingResult,
    ) -> tuple[str, str, Path, Optional[Path]]:
        """Resolve prefix/extension and effective paths for candidate routing."""
        manager = self._manager
        effective_path = Path(preprocessed.effective_path)

        # Start from preprocessed path metadata so overrides can adjust it.
        parse_target = manager._strip_internal_stage_suffix(effective_path)
        prefix, extension = parse_filename(str(parse_target))
        if preprocessed.prefix_override:
            prefix = preprocessed.prefix_override
        if preprocessed.extension_override:
            extension = preprocessed.extension_override

        if not effective_path.exists():
            effective_path = request.source
            # Keep metadata aligned with the true source path when preprocessing returns
            # an alias path that does not exist (important for exception routing suffixes).
            parse_target = manager._strip_internal_stage_suffix(effective_path)
            prefix, extension = parse_filename(str(parse_target))

        preprocessed_path = None
        explicit_path = Path(preprocessed.effective_path)
        if explicit_path != effective_path and explicit_path.exists():
            preprocessed_path = explicit_path

        return prefix, extension, effective_path, preprocessed_path

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

    def _route_decision_stage(self, candidate: ProcessingCandidate) -> RouteContext:
        """Resolve routing decision context for a candidate artifact."""
        return self._build_route_context(candidate)

    def _dispatch_route(self, context: RouteContext) -> ProcessingResult:
        if context.decision is RoutingDecision.ACCEPT:
            return self._persist_and_sync_stage(context)

        return self._non_accept_route_stage(context)

    def _persist_and_sync_stage(self, context: RouteContext) -> ProcessingResult:
        """Persist processed output and trigger sync behavior for accepted routes."""
        manager = self._manager
        final_path = manager._persist_candidate_record_stage(context)
        if final_path is None:
            return ProcessingResult(ProcessingStatus.PROCESSED, "Processed item")
        return ProcessingResult(ProcessingStatus.PROCESSED, "Processed item", Path(final_path))

    def _non_accept_route_stage(self, context: RouteContext) -> ProcessingResult:
        """Handle non-ACCEPT routing outcomes (rename-required or unappendable)."""
        manager = self._manager
        candidate = context.candidate

        def rename_delegate(path, prefix, ext, contextual_reason=None):
            return self._invoke_rename_flow(candidate, prefix, ext, contextual_reason)

        if context.decision is RoutingDecision.UNAPPENDABLE:
            return handle_unappendable_record(manager.interactions, rename_delegate, context)

        # Remaining non-ACCEPT cases fall back to the rename flow.
        return self._invoke_rename_flow(candidate, candidate.prefix, candidate.extension)

    def _invoke_rename_flow(
        self,
        candidate: ProcessingCandidate,
        current_prefix: str,
        extension: str,
        contextual_reason: Optional[str] = None,
    ) -> ProcessingResult:
        manager = self._manager
        retry_prefix = current_prefix
        retry_reason = contextual_reason

        while True:
            # UI-driven rename can either supply a sanitized prefix or bail out to manual processing.
            outcome = manager._rename_service.obtain_valid_prefix(retry_prefix, retry_reason)
            if outcome.cancelled or not outcome.sanitized_prefix:
                manager._rename_service.send_to_manual_bucket(
                    str(candidate.effective_path), retry_prefix, extension
                )
                FILES_FAILED.inc()
                return ProcessingResult(ProcessingStatus.REJECTED, "Rename cancelled by user")

            updated_candidate = replace(candidate, prefix=outcome.sanitized_prefix)
            context = self._route_decision_stage(updated_candidate)
            if context.decision is RoutingDecision.ACCEPT:
                return self._persist_and_sync_stage(context)

            retry_prefix, retry_reason = self._rename_retry_policy_stage(context)

    def _rename_retry_policy_stage(
        self,
        context: RouteContext,
    ) -> tuple[str, Optional[str]]:
        """Return next rename-loop prompt policy for non-ACCEPT routing outcomes."""
        manager = self._manager
        if context.decision is RoutingDecision.UNAPPENDABLE:
            manager.interactions.show_warning(
                WarningMessages.INVALID_RECORD,
                WarningMessages.INVALID_RECORD_DETAILS,
            )
            return (
                context.sanitized_prefix,
                DialogPrompts.UNAPPENDABLE_RECORD_CONTEXT.format(
                    record_id=context.sanitized_prefix
                ),
            )
        return context.candidate.prefix, None

    def _route_with_prefix(self, candidate: ProcessingCandidate, prefix_override: str) -> ProcessingResult:
        updated = replace(candidate, prefix=prefix_override)
        context = self._route_decision_stage(updated)
        if context.decision is RoutingDecision.ACCEPT:
            return self._persist_and_sync_stage(context)
        return self._non_accept_route_stage(context)

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
        self._modified_event_gate = ModifiedEventGate(
            self.config_service,
            self._resolve_processor,
        )

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

    def should_queue_modified(self, path: str) -> bool:
        """Return True when a modified event should be queued for processing."""
        return self._modified_event_gate.should_queue(path)

    def add_item_to_record(
        self,
        record,
        src_path: str,
        filename_prefix: str,
        extension: str,
        file_processor: Optional[FileProcessorABS] = None,
        device: DeviceConfig | None = None,
    ) -> Optional[str]:
        processor = file_processor or self.file_processor
        if processor is None:
            move_to_exception_folder(src_path)
            FILES_FAILED.inc()
            raise RuntimeError("No file processor available")

        (
            record,
            processor,
            record_path,
            file_id,
        ) = self._resolve_record_persistence_context_stage(
            record,
            filename_prefix,
            device,
            processor,
        )
        output: ProcessingOutput = self._process_record_artifact_stage(
            processor,
            src_path,
            record_path,
            file_id,
            extension,
        )

        self._assign_record_datatype_stage(record, output)
        return self._finalize_record_output_stage(
            output,
            record,
            record_path,
            src_path,
        )

    def _resolve_record_persistence_context_stage(
        self,
        record: LocalRecord | None,
        filename_prefix: str,
        device: DeviceConfig | None,
        processor: FileProcessorABS,
    ) -> tuple[LocalRecord, FileProcessorABS, str, str]:
        """Resolve record, processor context, and naming paths for persistence."""
        resolved_device = device or self.config_service.current_device()
        resolved_record = get_or_create_record(
            self.records,
            record,
            filename_prefix,
            resolved_device,
        )
        device_abbr = (
            resolved_device.metadata.device_abbr if resolved_device else None
        )
        apply_device_defaults(resolved_record, resolved_device)
        record_path = get_record_path(filename_prefix, device_abbr)
        file_id = generate_file_id(filename_prefix, device_abbr)
        return resolved_record, processor, record_path, file_id

    def _process_record_artifact_stage(
        self,
        processor: FileProcessorABS,
        src_path: str,
        record_path: str,
        file_id: str,
        extension: str,
    ) -> ProcessingOutput:
        """Invoke processor and return normalized output for record persistence."""
        return processor.device_specific_processing(
            src_path,
            record_path,
            file_id,
            extension,
        )

    def _assign_record_datatype_stage(
        self,
        record,
        output: ProcessingOutput,
    ) -> None:
        """Assign processor-reported datatype onto the target record."""
        record.datatype = output.datatype

    def _finalize_record_output_stage(
        self,
        output: ProcessingOutput,
        record,
        record_path: str,
        src_path: str,
    ) -> str:
        """Finalize persistence side effects and return the output path."""
        logger.debug("Processed %s -> %s", src_path, output.final_path)
        self._post_persist_side_effects_stage(output, record, record_path, src_path)
        return output.final_path

    def _post_persist_side_effects_stage(
        self,
        output: ProcessingOutput,
        record,
        record_path: str,
        src_path: str,
    ) -> None:
        """Apply post-persist bookkeeping, metrics, and immediate sync policy."""
        new_files = update_record(self.records, output.final_path, record)
        if output.force_paths:
            for force_path in output.force_paths:
                if not force_path:
                    continue
                path_obj = Path(force_path)
                if not path_obj.is_absolute():
                    path_obj = Path(record_path) / path_obj
                if not path_obj.exists():
                    logger.debug("Skipping missing force path for record: %s", force_path)
                    continue
                new_files += update_record(self.records, str(path_obj), record)
                if path_obj.is_dir():
                    for child in path_obj.rglob("*"):
                        if child.is_file():
                            record.mark_file_as_unsynced(str(child))
                else:
                    record.mark_file_as_unsynced(str(path_obj))
        if new_files > 0:
            FILES_PROCESSED.inc(new_files)

        # Immediate sync path (best-effort) — keeps prior startup sync logic.
        if self._immediate_sync:
            try:
                if not self.records.all_records_uploaded():
                    self.records.sync_records_to_database()
            except Exception as exc:  # noqa: BLE001
                logger.exception("Immediate sync failed after processing %s: %s", src_path, exc)

    def _persist_candidate_record_stage(self, context: RouteContext) -> Optional[str]:
        """Persist accepted candidate artifact and return final output path."""
        candidate = context.candidate
        return self.add_item_to_record(
            context.existing_record,
            str(candidate.effective_path),
            context.sanitized_prefix,
            candidate.extension,
            candidate.processor,
            device=candidate.device,
        )

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
