"""Internal multi-stage processing pipeline used by FileProcessManager."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from dpost.application.metrics import FILES_FAILED
from dpost.application.naming.policy import parse_filename
from dpost.application.processing.candidate_metadata import derive_candidate_metadata
from dpost.application.processing.device_resolver import DeviceResolutionKind
from dpost.application.processing.file_processor_abstract import (
    FileProcessorABS,
    PreprocessingResult,
)
from dpost.application.processing.record_flow import handle_unappendable_record
from dpost.application.processing.rename_retry_policy import build_rename_retry_prompt
from dpost.application.processing.route_context_policy import build_route_context
from dpost.application.processing.routing import fetch_record_for_prefix
from dpost.application.processing.stability_tracker import FileStabilityTracker
from dpost.domain.processing.models import (
    ProcessingCandidate,
    ProcessingRequest,
    ProcessingResult,
    ProcessingStatus,
    RouteContext,
    RoutingDecision,
)
from dpost.infrastructure.logging import setup_logger

if TYPE_CHECKING:
    from dpost.application.processing.file_process_manager import FileProcessManager

logger = setup_logger(__name__)


class _ProcessingPipeline:
    """Internal helper that orchestrates the multi-stage processing pipeline."""

    def __init__(self, manager: FileProcessManager) -> None:
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
        reason = resolution.reason or "Invalid file type"
        if resolution.kind is DeviceResolutionKind.DEFER:
            logger.debug("Processing deferred for %s: %s", path, reason)
            return ProcessingResult(
                ProcessingStatus.DEFERRED,
                reason,
                retry_delay=resolution.retry_delay,
            )
        if resolution.kind is DeviceResolutionKind.REJECT:
            return self._reject_immediately(path, reason)
        assert device is not None  # ACCEPT outcomes guarantee a selected device.
        return ProcessingRequest(source=path, device=device)

    def _stabilize_artifact_stage(
        self,
        request: ProcessingRequest,
    ) -> ProcessingRequest | ProcessingResult:
        manager = self._manager
        # Block until the artefact stops changing (device overrides can tweak thresholds).
        stability_outcome = FileStabilityTracker(request.source, request.device).wait()
        if stability_outcome.deferred:
            reason = stability_outcome.reason or "File deferred by stability guard"
            logger.debug("Processing deferred for %s: %s", request.source, reason)
            return ProcessingResult(
                ProcessingStatus.DEFERRED,
                reason,
                retry_delay=stability_outcome.retry_delay,
            )
        if stability_outcome.rejected:
            reason = stability_outcome.reason or "File rejected by stability guard"
            manager._register_rejection(str(request.source), reason)
            manager._safe_move_to_exception_with_context(str(request.source))
            FILES_FAILED.inc()
            return ProcessingResult(ProcessingStatus.REJECTED, reason)
        if not request.source.exists():
            reason = f"Path '{request.source.name}' disappeared before stability confirmation"
            logger.debug("Processing deferred for %s: %s", request.source, reason)
            return ProcessingResult(ProcessingStatus.DEFERRED, reason)
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
        active_config = manager.config_service.current
        sanitized_prefix, is_valid_format, record = fetch_record_for_prefix(
            manager.records,
            candidate.prefix,
            candidate.device,
            filename_pattern=active_config.filename_pattern,
            id_separator=active_config.id_separator,
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
            active_config = manager.config_service.current
            outcome = manager._rename_service.obtain_valid_prefix(
                retry_prefix,
                retry_reason,
                filename_pattern=active_config.filename_pattern,
                id_separator=active_config.id_separator,
            )
            if outcome.cancelled or not outcome.sanitized_prefix:
                manager._rename_service.send_to_manual_bucket(
                    str(candidate.effective_path),
                    retry_prefix,
                    extension,
                    rename_dir=str(active_config.paths.rename_dir),
                    id_separator=active_config.id_separator,
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
        manager._move_to_exception_bucket_stage(str(path))
        manager._register_rejection(str(path), reason)
        FILES_FAILED.inc()
        return ProcessingResult(ProcessingStatus.REJECTED, reason)
