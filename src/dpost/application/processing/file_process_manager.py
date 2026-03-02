"""Coordinated file ingestion pipeline that hands off to device plugins."""

from __future__ import annotations

import queue
import re
from pathlib import Path
from typing import Optional, Tuple

from dpost.application.config import ConfigService, DeviceConfig
from dpost.application.metrics import FILES_FAILED, FILES_PROCESSED
from dpost.application.naming.policy import generate_file_id
from dpost.application.ports import SyncAdapterPort, UserInteractionPort
from dpost.application.processing.device_resolver import DeviceResolver
from dpost.application.processing.error_handling import safe_move_to_exception
from dpost.application.processing.failure_emitter import (
    ProcessingFailureEmissionSink,
    emit_processing_failure_outcome,
)
from dpost.application.processing.failure_outcome_policy import (
    ProcessingFailureOutcome,
    build_processing_failure_outcome,
)
from dpost.application.processing.file_processor_abstract import (
    FileProcessorABS,
    ProcessingOutput,
)
from dpost.application.processing.force_path_policy import (
    iter_force_unsynced_targets,
    resolve_force_paths,
)
from dpost.application.processing.immediate_sync_error_emitter import (
    ImmediateSyncErrorEmissionSink,
    emit_immediate_sync_error,
)
from dpost.application.processing.modified_event_gate import ModifiedEventGate
from dpost.application.processing.post_persist_bookkeeping import (
    PostPersistBookkeepingEmissionSink,
    PostPersistBookkeepingPlan,
    build_post_persist_bookkeeping_plan,
    emit_post_persist_bookkeeping,
)
from dpost.application.processing.processing_pipeline import _ProcessingPipeline
from dpost.application.processing.processing_pipeline_runtime import (
    ProcessingPipelineRuntime,
)
from dpost.application.processing.processor_factory import FileProcessorFactory
from dpost.application.processing.processor_runtime_context import (
    apply_processor_runtime_context,
    build_processor_runtime_context,
)
from dpost.application.processing.record_persistence_context import (
    RecordPersistenceContext,
    build_record_persistence_context,
)
from dpost.application.processing.record_utils import (
    apply_device_defaults,
    get_or_create_record,
    update_record,
)
from dpost.application.processing.rename_flow import RenameService
from dpost.application.records.record_manager import RecordManager
from dpost.application.session import SessionManager
from dpost.domain.processing.models import (
    ProcessingCandidate,
    ProcessingResult,
    RouteContext,
)
from dpost.domain.records.local_record import LocalRecord
from dpost.infrastructure.logging import setup_logger
from dpost.infrastructure.storage.filesystem_utils import (
    get_record_path,
    move_to_exception_folder,
)

logger = setup_logger(__name__)

# Recognises artefacts parked in our hidden staging folders (created during preprocessing retries).
_INTERNAL_STAGING_SUFFIX_RE = re.compile(
    r"\.__staged__(\d+)?",
    re.IGNORECASE,
)


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
        config_service: ConfigService,
        file_processor: FileProcessorABS | None = None,
        immediate_sync: bool = False,
        failure_emission_sink: ProcessingFailureEmissionSink | None = None,
        immediate_sync_error_sink: ImmediateSyncErrorEmissionSink | None = None,
    ) -> None:
        self.interactions = interactions
        self.session_manager = session_manager
        self.config_service = config_service
        self.file_processor = file_processor
        active_config = self.config_service.current
        self.records = RecordManager(
            sync_manager=sync_manager,
            persisted_records_path=active_config.paths.daily_records_json,
            id_separator=active_config.id_separator,
        )
        self._processor_factory = FileProcessorFactory()
        self._device_resolver = DeviceResolver(
            self.config_service, self._processor_factory
        )
        self._rename_service = RenameService(interactions)
        self._rejected_queue: queue.Queue[Tuple[str, str]] = queue.Queue()
        self._failure_emission_sink = (
            failure_emission_sink or self._default_failure_emission_sink()
        )
        self._immediate_sync_error_sink = (
            immediate_sync_error_sink or self._default_immediate_sync_error_sink()
        )
        self._pipeline_runtime = ProcessingPipelineRuntime(self)
        self._pipeline = _ProcessingPipeline(self._pipeline_runtime)
        self._immediate_sync = immediate_sync
        self._startup_sync_attempted = False
        self._modified_event_gate = ModifiedEventGate(
            self.config_service,
            self._resolve_processor,
        )

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

    def run_startup_sync_if_pending(self) -> None:
        """Run the one-time startup sync check explicitly from composition boundaries."""
        if self._startup_sync_attempted:
            return
        self._startup_sync_attempted = True
        if not self.records.all_records_uploaded():
            logger.debug("Syncing records to database upon startup")
            self.sync_records_to_database()

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
            self._move_to_exception_bucket_stage(source_path)
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
        active_config = self.config_service.current
        context: RecordPersistenceContext = build_record_persistence_context(
            records=self.records,
            existing_record=record,
            filename_prefix=filename_prefix,
            device=device,
            processor=processor,
            id_separator=active_config.id_separator,
            dest_dir=active_config.paths.dest_dir,
            current_device_provider=self.config_service.current_device,
            get_or_create_record_fn=get_or_create_record,
            apply_device_defaults_fn=apply_device_defaults,
            get_record_path_fn=get_record_path,
            generate_file_id_fn=generate_file_id,
        )
        return (
            context.record,
            context.processor,
            context.record_path,
            context.file_id,
        )

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
        bookkeeping_plan = self._build_post_persist_bookkeeping_plan_stage(
            output,
            record_path,
        )
        self._log_post_persist_bookkeeping_skips_stage(bookkeeping_plan)
        self._emit_post_persist_bookkeeping_stage(bookkeeping_plan, record)

        # Immediate sync path (best-effort) — keeps prior startup sync logic.
        if self._immediate_sync:
            try:
                if not self.records.all_records_uploaded():
                    self.records.sync_records_to_database()
            except Exception as exc:  # noqa: BLE001
                self._emit_immediate_sync_error_stage(src_path, exc)

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
            processor = self.file_processor
        else:
            # Fall back to loading a processor via the factory based on the resolved device.
            # The factory caches instances per device, so repeated calls are inexpensive.
            processor = self._processor_factory.get_for_device(device.identifier)
        # Apply runtime context after construction to reduce processor-global config lookups.
        runtime_context = build_processor_runtime_context(self.config_service.current)
        apply_processor_runtime_context(processor, device, runtime_context)
        return processor

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

    @staticmethod
    def _log_processing_failure_exception(path: Path, exc: Exception) -> None:
        """Log processing failures at exception level with source path context."""
        logger.exception("Error processing %s: %s", path, exc)

    def _default_failure_emission_sink(self) -> ProcessingFailureEmissionSink:
        """Build the default sink that applies manager failure side effects."""
        return ProcessingFailureEmissionSink(
            log_exception=self._log_processing_failure_exception,
            move_to_exception=self._safe_move_to_exception_with_context,
            register_rejection=self._register_rejection,
            increment_failed_metric=FILES_FAILED.inc,
        )

    def _move_to_exception_bucket_stage(
        self,
        src_path: str,
        filename_prefix: str | None = None,
        extension: str | None = None,
    ) -> None:
        """Move an artefact to the exception bucket using explicit config context."""
        active_config = self.config_service.current
        move_to_exception_folder(
            src_path,
            filename_prefix,
            extension,
            base_dir=str(active_config.paths.exceptions_dir),
            id_separator=active_config.id_separator,
        )

    def _safe_move_to_exception_with_context(
        self,
        src_path: str,
        filename_prefix: str | None = None,
        extension: str | None = None,
    ) -> None:
        """Safely move an artefact to exceptions using explicit config context."""
        active_config = self.config_service.current
        safe_move_to_exception(
            src_path,
            filename_prefix,
            extension,
            exception_dir=str(active_config.paths.exceptions_dir),
            id_separator=active_config.id_separator,
        )

    @staticmethod
    def _log_immediate_sync_exception(src_path: str, exc: Exception) -> None:
        """Log immediate-sync failures with source path context."""
        logger.exception("Immediate sync failed after processing %s: %s", src_path, exc)

    def _default_immediate_sync_error_sink(self) -> ImmediateSyncErrorEmissionSink:
        """Build the default sink for immediate-sync error side effects."""
        return ImmediateSyncErrorEmissionSink(
            log_exception=self._log_immediate_sync_exception,
            show_error=self.interactions.show_error,
        )

    def _build_post_persist_bookkeeping_plan_stage(
        self,
        output: ProcessingOutput,
        record_path: str,
    ) -> PostPersistBookkeepingPlan:
        """Build record-update and unsynced-marking work for a processed artifact."""
        resolved_force_paths = tuple()
        if output.force_paths:
            resolved_force_paths = resolve_force_paths(output.force_paths, record_path)
        return build_post_persist_bookkeeping_plan(
            output.final_path,
            resolved_force_paths,
            iter_force_unsynced_targets_fn=iter_force_unsynced_targets,
        )

    @staticmethod
    def _log_post_persist_bookkeeping_skips_stage(
        plan: PostPersistBookkeepingPlan,
    ) -> None:
        """Log skipped force-path entries that were missing at emit time."""
        for raw_path in plan.skipped_missing_force_paths:
            logger.debug("Skipping missing force path for record: %s", raw_path)

    def _build_post_persist_bookkeeping_sink(
        self,
        record,
    ) -> PostPersistBookkeepingEmissionSink:
        """Build the default sink for post-persist record bookkeeping side effects."""
        return PostPersistBookkeepingEmissionSink(
            update_record=lambda path: update_record(self.records, path, record),
            mark_file_as_unsynced=record.mark_file_as_unsynced,
            increment_processed_metric=FILES_PROCESSED.inc,
        )

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
        emit_processing_failure_outcome(
            path,
            exc,
            failure_outcome,
            self._failure_emission_sink,
        )

    def _emit_immediate_sync_error_stage(self, src_path: str, exc: Exception) -> None:
        """Apply immediate-sync failure logging and user error reporting."""
        emit_immediate_sync_error(src_path, exc, self._immediate_sync_error_sink)

    def _emit_post_persist_bookkeeping_stage(
        self,
        plan: PostPersistBookkeepingPlan,
        record,
    ) -> int:
        """Apply post-persist bookkeeping side effects and return new-file count."""
        return emit_post_persist_bookkeeping(
            plan,
            self._build_post_persist_bookkeeping_sink(record),
        )
