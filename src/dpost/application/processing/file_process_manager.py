"""Coordinated file ingestion pipeline that hands off to device plugins."""

from __future__ import annotations

import queue
import re
from dataclasses import replace
from pathlib import Path
from typing import Optional, Tuple

from dpost.application.config import ConfigService, DeviceConfig, get_service
from dpost.application.naming.policy import generate_file_id, parse_filename
from dpost.application.interactions import (
    ErrorMessages,
)
from dpost.application.metrics import FILES_FAILED, FILES_PROCESSED
from dpost.application.ports import SyncAdapterPort
from dpost.application.ports import UserInteractionPort
from dpost.domain.processing.models import (
    ProcessingCandidate,
    ProcessingRequest,
    ProcessingResult,
    ProcessingStatus,
    RouteContext,
    RoutingDecision,
)
from dpost.infrastructure.logging import setup_logger
from dpost.infrastructure.storage.filesystem_utils import (
    get_record_path,
    move_to_exception_folder,
)
from dpost.application.session import SessionManager
from dpost.application.processing.device_resolver import DeviceResolver
from dpost.application.processing.error_handling import safe_move_to_exception
from dpost.application.processing.candidate_metadata import derive_candidate_metadata
from dpost.application.processing.failure_outcome_policy import (
    ProcessingFailureOutcome,
    build_processing_failure_outcome,
)
from dpost.application.processing.file_processor_abstract import (
    FileProcessorABS,
    PreprocessingResult,
    ProcessingOutput,
)
from dpost.application.processing.force_path_policy import (
    iter_force_unsynced_targets,
    resolve_force_paths,
)
from dpost.application.processing.modified_event_gate import ModifiedEventGate
from dpost.application.processing.processor_factory import FileProcessorFactory
from dpost.application.processing.record_flow import handle_unappendable_record
from dpost.application.processing.route_context_policy import build_route_context
from dpost.application.processing.rename_retry_policy import build_rename_retry_prompt
from dpost.application.processing.record_utils import (
    apply_device_defaults,
    get_or_create_record,
    update_record,
)
from dpost.application.processing.rename_flow import RenameService
from dpost.application.processing.routing import fetch_record_for_prefix
from dpost.application.processing.stability_tracker import FileStabilityTracker
from dpost.application.records.record_manager import RecordManager
from dpost.domain.records.local_record import LocalRecord

logger = setup_logger(__name__)

# Recognises artefacts parked in our hidden staging folders (created during preprocessing retries).
_INTERNAL_STAGING_SUFFIX_RE = re.compile(
    r"\.__staged__(\d+)?",
    re.IGNORECASE,
)


class _ProcessingPipeline:
    """Internal helper that orchestrates the multi-stage processing pipeline."""

    def __init__(self, manager: "FileProcessManager") -> None:
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
            raise RuntimeError(
                f"File processing failed for {request.source}: {exc}"
            ) from exc
        # Defensive exhaustiveness guard; all valid control flow paths return or raise above.
        raise RuntimeError("Unreachable code in _execute_pipeline")  # pragma: no cover

    def _preprocess_stage(
        self,
        request: ProcessingRequest,
        processor: FileProcessorABS,
    ) -> ProcessingCandidate | ProcessingResult:
        """Run preprocessing and return a routable candidate or deferred result."""
        return self._build_candidate(request, processor)

    def _build_candidate(
        self, request: ProcessingRequest, processor: FileProcessorABS
    ) -> ProcessingCandidate | ProcessingResult:
        preprocessed = processor.device_specific_preprocessing(str(request.source))
        if preprocessed is None:
            return ProcessingResult(
                ProcessingStatus.DEFERRED, "Awaiting paired artefacts"
            )
        assert isinstance(
            preprocessed, PreprocessingResult
        )  # type narrowing for Pylance

        prefix, extension, effective_path, preprocessed_path = (
            self._derive_candidate_metadata(request, preprocessed)
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
        metadata = derive_candidate_metadata(
            request.source,
            preprocessed,
            strip_internal_stage_suffix=self._manager._strip_internal_stage_suffix,
            parse_filename_fn=parse_filename,
        )
        return (
            metadata.prefix,
            metadata.extension,
            metadata.effective_path,
            metadata.preprocessed_path,
        )

    def _build_route_context(self, candidate: ProcessingCandidate) -> RouteContext:
        manager = self._manager
        sanitized_prefix, is_valid_format, record = fetch_record_for_prefix(
            manager.records, candidate.prefix, candidate.device
        )
        return build_route_context(
            candidate,
            sanitized_prefix,
            record,
            is_valid_format,
        )

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
        return ProcessingResult(
            ProcessingStatus.PROCESSED, "Processed item", Path(final_path)
        )

    def _non_accept_route_stage(self, context: RouteContext) -> ProcessingResult:
        """Handle non-ACCEPT routing outcomes (rename-required or unappendable)."""
        manager = self._manager
        candidate = context.candidate

        def rename_delegate(path, prefix, ext, contextual_reason=None):
            return self._invoke_rename_flow(candidate, prefix, ext, contextual_reason)

        if context.decision is RoutingDecision.UNAPPENDABLE:
            return handle_unappendable_record(
                manager.interactions, rename_delegate, context
            )

        # Remaining non-ACCEPT cases fall back to the rename flow.
        return self._invoke_rename_flow(
            candidate, candidate.prefix, candidate.extension
        )

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
            outcome = manager._rename_service.obtain_valid_prefix(
                retry_prefix, retry_reason
            )
            if outcome.cancelled or not outcome.sanitized_prefix:
                manager._rename_service.send_to_manual_bucket(
                    str(candidate.effective_path), retry_prefix, extension
                )
                FILES_FAILED.inc()
                return ProcessingResult(
                    ProcessingStatus.REJECTED, "Rename cancelled by user"
                )

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
        policy = build_rename_retry_prompt(context)
        if policy.warning_title and policy.warning_message:
            manager.interactions.show_warning(
                policy.warning_title,
                policy.warning_message,
            )
        return policy.next_prefix, policy.contextual_reason

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
        sync_manager: SyncAdapterPort,
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
        self._device_resolver = DeviceResolver(
            self.config_service, self._processor_factory
        )
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
        processor = self._resolve_record_processor_stage(file_processor, src_path)

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

    def _resolve_record_processor_stage(
        self,
        file_processor: Optional[FileProcessorABS],
        source_path: str,
    ) -> FileProcessorABS:
        """Resolve processor for record persistence or fail with routing fallback behavior."""
        processor = file_processor or self.file_processor
        if processor is None:
            move_to_exception_folder(source_path)
            FILES_FAILED.inc()
            raise RuntimeError("No file processor available")
        return processor

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
        device_abbr = resolved_device.metadata.device_abbr if resolved_device else None
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
            for resolved in resolve_force_paths(output.force_paths, record_path):
                if not resolved.exists:
                    logger.debug(
                        "Skipping missing force path for record: %s", resolved.raw_path
                    )
                    continue
                new_files += update_record(
                    self.records, str(resolved.resolved_path), record
                )
                for child in iter_force_unsynced_targets(resolved.resolved_path):
                    record.mark_file_as_unsynced(str(child))
        if new_files > 0:
            FILES_PROCESSED.inc(new_files)

        # Immediate sync path (best-effort) — keeps prior startup sync logic.
        if self._immediate_sync:
            try:
                if not self.records.all_records_uploaded():
                    self.records.sync_records_to_database()
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "Immediate sync failed after processing %s: %s", src_path, exc
                )
                self.interactions.show_error(
                    ErrorMessages.SYNC_ERROR,
                    ErrorMessages.SYNC_ERROR_DETAILS.format(
                        filename=Path(src_path).name,
                        error=exc,
                    ),
                )

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
        new_name = _INTERNAL_STAGING_SUFFIX_RE.sub("", name)
        return path.with_name(new_name)

    @staticmethod
    def _is_internal_staging_path(path: Path) -> bool:
        if _INTERNAL_STAGING_SUFFIX_RE.search(path.name):
            return True
        return any(
            _INTERNAL_STAGING_SUFFIX_RE.search(parent.name) for parent in path.parents
        )

    def _register_rejection(self, path: str, reason: str) -> None:
        logger.warning("Rejected %s: %s", path, reason)
        self._rejected_queue.put((path, reason))

    def _handle_processing_failure(
        self,
        path: Path,
        candidate: Optional[ProcessingCandidate],
        exc: Exception,
    ) -> None:
        failure_outcome = self._build_processing_failure_outcome_stage(
            path, candidate, exc
        )
        self._emit_processing_failure_outcome_stage(path, exc, failure_outcome)

    def _build_processing_failure_outcome_stage(
        self,
        path: Path,
        candidate: Optional[ProcessingCandidate],
        exc: Exception,
    ) -> ProcessingFailureOutcome:
        """Classify failure artifacts and rejection payload without side effects."""
        return build_processing_failure_outcome(path, candidate, exc)

    def _emit_processing_failure_outcome_stage(
        self,
        path: Path,
        exc: Exception,
        failure_outcome: ProcessingFailureOutcome,
    ) -> None:
        """Apply logging, file moves, queue registration, and metrics for a failure."""
        logger.exception("Error processing %s: %s", path, exc)
        self._emit_processing_failure_moves_stage(failure_outcome)
        self._emit_processing_failure_rejection_stage(failure_outcome)

    def _emit_processing_failure_moves_stage(
        self,
        failure_outcome: ProcessingFailureOutcome,
    ) -> None:
        """Move failure artifacts so watch folders do not retain partial inputs."""
        # Move whichever artefact exists (raw or preprocessed) so nothing lingers in watch folders.
        for move_target in failure_outcome.move_targets:
            safe_move_to_exception(
                move_target.path,
                move_target.prefix,
                move_target.extension,
            )

    def _emit_processing_failure_rejection_stage(
        self,
        failure_outcome: ProcessingFailureOutcome,
    ) -> None:
        """Register rejection payload and increment failure metrics."""
        self._register_rejection(
            failure_outcome.rejection_path,
            failure_outcome.rejection_reason,
        )
        FILES_FAILED.inc()
