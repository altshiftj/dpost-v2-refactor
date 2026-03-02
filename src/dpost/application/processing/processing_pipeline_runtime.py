"""Runtime adapter exposing FileProcessManager dependencies to the pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional

from dpost.application.processing.file_processor_abstract import FileProcessorABS
from dpost.application.processing.rename_flow import RenameOutcome
from dpost.domain.processing.models import ProcessingCandidate, RouteContext

if TYPE_CHECKING:
    from dpost.application.config import DeviceConfig
    from dpost.application.processing.device_resolver import DeviceResolution
    from dpost.application.processing.file_process_manager import FileProcessManager


class ProcessingPipelineRuntime:
    """Runtime adapter for pipeline access to manager-owned collaborators."""

    def __init__(self, manager: FileProcessManager) -> None:
        self._manager = manager

    @property
    def config_service(self):
        return self._manager.config_service

    @property
    def records(self):
        return self._manager.records

    @property
    def interactions(self):
        return self._manager.interactions

    def is_internal_staging_path(self, path: Path) -> bool:
        return self._manager._is_internal_staging_path(path)

    def strip_internal_stage_suffix(self, path: Path) -> Path:
        return self._manager._strip_internal_stage_suffix(path)

    def resolve_device(self, path: Path) -> DeviceResolution:
        return self._manager._device_resolver.resolve(path)

    def register_rejection(self, path: str, reason: str) -> None:
        self._manager._register_rejection(path, reason)

    def safe_move_to_exception_with_context(self, src_path: str) -> None:
        self._manager._safe_move_to_exception_with_context(src_path)

    def activate_device(self, device: DeviceConfig):
        return self._manager.config_service.activate_device(device)

    def resolve_processor(self, device: DeviceConfig) -> FileProcessorABS:
        return self._manager._resolve_processor(device)

    def handle_processing_failure(
        self,
        path: Path,
        candidate: Optional[ProcessingCandidate],
        exc: Exception,
    ) -> None:
        self._manager._handle_processing_failure(path, candidate, exc)

    def persist_candidate_record(self, context: RouteContext) -> Optional[str]:
        return self._manager._persist_candidate_record_stage(context)

    def move_to_exception_bucket(self, src_path: str) -> None:
        self._manager._move_to_exception_bucket_stage(src_path)

    def obtain_valid_prefix(
        self,
        retry_prefix: str,
        retry_reason: str | None,
    ) -> RenameOutcome:
        active_config = self._manager.config_service.current
        return self._manager._rename_service.obtain_valid_prefix(
            retry_prefix,
            retry_reason,
            filename_pattern=active_config.filename_pattern,
            id_separator=active_config.id_separator,
        )

    def send_to_manual_bucket(
        self,
        effective_path: str,
        retry_prefix: str,
        extension: str,
    ) -> None:
        active_config = self._manager.config_service.current
        self._manager._rename_service.send_to_manual_bucket(
            effective_path,
            retry_prefix,
            extension,
            rename_dir=str(active_config.paths.rename_dir),
            id_separator=active_config.id_separator,
        )
