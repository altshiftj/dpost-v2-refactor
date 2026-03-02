"""Processor for ERM HIOKI exports under canonical dpost namespace."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Pattern

from dpost.application.config import DeviceConfig
from dpost.application.naming.policy import is_valid_prefix
from dpost.application.processing.file_processor_abstract import (
    FileProbeResult,
    FileProcessorABS,
    PreprocessingResult,
    ProcessingOutput,
)
from dpost.domain.records.local_record import LocalRecord
from dpost.infrastructure.logging import setup_logger
from dpost.infrastructure.storage.filesystem_utils import get_unique_filename, move_item

logger = setup_logger(__name__)

_MEASUREMENT_SUFFIX_RE = re.compile(r"_(\d{14})$")
_CC_PREFIX_RE = re.compile(r"^cc_", re.IGNORECASE)


class FileProcessorHioki(FileProcessorABS):
    """Handle Hioki CSV outputs plus optional Excel exports."""

    def __init__(
        self,
        device_config: DeviceConfig,
        *,
        id_separator: str | None = None,
        filename_pattern: Pattern[str] | None = None,
    ) -> None:
        super().__init__(device_config)
        self.device_config = device_config
        self._id_separator = id_separator
        self._filename_pattern = filename_pattern

    def configure_runtime_context(
        self,
        *,
        id_separator: str | None = None,
        filename_pattern: Pattern[str] | None = None,
        dest_dir: str | None = None,
        rename_dir: str | None = None,
        exception_dir: str | None = None,
        current_device=None,
    ) -> None:
        """Capture runtime naming context when constructed without explicit values."""
        if self._id_separator is None and id_separator is not None:
            self._id_separator = id_separator
        if self._filename_pattern is None and filename_pattern is not None:
            self._filename_pattern = filename_pattern

    def device_specific_preprocessing(self, path: str) -> PreprocessingResult | None:
        """Normalize measurement prefixes before routing."""
        candidate = Path(path)
        if candidate.suffix.lower() != ".csv":
            return PreprocessingResult.passthrough(path)

        normalized = self._normalize_stem(candidate.stem)
        if normalized != candidate.stem:
            return PreprocessingResult.with_prefix(path, normalized)
        return PreprocessingResult.passthrough(path)

    def probe_file(self, filepath: str) -> FileProbeResult:
        """Probe by exported extension compatibility."""
        target = Path(filepath)
        ext = target.suffix.lower()

        if ext in self.device_config.files.exported_extensions:
            return FileProbeResult.match(
                confidence=0.6,
                reason="Excel export for Hioki analyzer",
            )
        return FileProbeResult.mismatch(
            "Unsupported extension for Hioki (Excel expected)"
        )

    def should_queue_modified(self, path: str) -> bool:
        target = Path(path)
        if target.suffix.lower() != ".csv":
            return False
        if self._id_separator is None or self._filename_pattern is None:
            return False
        stem = target.stem
        if self._is_measurement(stem):
            return False
        if self._is_cc(stem):
            return is_valid_prefix(
                self._normalize_stem(stem),
                filename_pattern=self._filename_pattern,
                id_separator=self._id_separator,
            )
        return is_valid_prefix(
            stem,
            filename_pattern=self._filename_pattern,
            id_separator=self._id_separator,
        )

    def is_appendable(
        self, record: LocalRecord, filename_prefix: str, extension: str
    ) -> bool:
        return True

    @classmethod
    def get_device_id(cls) -> str:
        return "hioki_blb"

    def device_specific_processing(
        self,
        src_path: str,
        record_path: str,
        file_id: str,
        extension: str,
    ) -> ProcessingOutput:
        """Route Hioki artefacts while preserving overwrite/force-upload rules."""
        src = Path(src_path)
        record_dir = Path(record_path)
        record_dir.mkdir(parents=True, exist_ok=True)
        ext = self._resolve_extension(src, extension)

        if ext in {".xlsx", ".xls"}:
            return self._process_excel(src_path, record_path, file_id, ext)
        if ext != ".csv":
            return self._process_generic(src_path, record_path, file_id, ext)

        stem = src.stem
        if self._is_measurement(stem):
            return self._process_measurement_csv(src, record_dir, file_id, ext)
        if self._is_cc(stem):
            return self._process_cc_csv(src, record_dir, file_id)
        return self._process_aggregate_csv(src, record_dir, file_id)

    def _process_excel(
        self,
        src_path: str,
        record_path: str,
        file_id: str,
        extension: str,
    ) -> ProcessingOutput:
        destination = get_unique_filename(
            record_path,
            file_id,
            extension,
            id_separator=self._runtime_id_separator(),
        )
        move_item(src_path, destination)
        return ProcessingOutput(final_path=destination, datatype="hioki")

    def _process_generic(
        self,
        src_path: str,
        record_path: str,
        file_id: str,
        extension: str,
    ) -> ProcessingOutput:
        destination = get_unique_filename(
            record_path,
            file_id,
            extension,
            id_separator=self._runtime_id_separator(),
        )
        move_item(src_path, destination)
        return ProcessingOutput(final_path=destination, datatype="hioki")

    def _process_measurement_csv(
        self,
        src: Path,
        record_dir: Path,
        file_id: str,
        extension: str,
    ) -> ProcessingOutput:
        destination = get_unique_filename(
            str(record_dir),
            file_id,
            extension,
            id_separator=self._runtime_id_separator(),
        )
        move_item(src, destination)

        base = self._normalize_stem(src.stem)
        force_paths: list[str] = []

        self._maybe_copy_force(
            src.parent / f"CC_{base}.csv",
            self._cc_dest(record_dir, file_id),
            force_paths,
        )
        self._maybe_copy_force(
            src.parent / f"{base}.csv",
            self._results_dest(record_dir, file_id),
            force_paths,
        )

        return ProcessingOutput(
            final_path=destination,
            datatype="hioki",
            force_paths=tuple(force_paths),
        )

    def _process_cc_csv(
        self,
        src: Path,
        record_dir: Path,
        file_id: str,
    ) -> ProcessingOutput:
        cc_dest = self._cc_dest(record_dir, file_id)
        self._copy_overwrite(src, cc_dest)
        return ProcessingOutput(
            final_path=str(cc_dest),
            datatype="hioki",
            force_paths=(str(cc_dest),),
        )

    def _process_aggregate_csv(
        self,
        src: Path,
        record_dir: Path,
        file_id: str,
    ) -> ProcessingOutput:
        aggregate_dest = self._results_dest(record_dir, file_id)
        self._copy_overwrite(src, aggregate_dest)
        return ProcessingOutput(
            final_path=str(aggregate_dest),
            datatype="hioki",
            force_paths=(str(aggregate_dest),),
        )

    @staticmethod
    def _resolve_extension(src: Path, extension: str) -> str:
        ext = src.suffix.lower()
        return ext if ext else extension.lower()

    @staticmethod
    def _cc_dest(record_dir: Path, file_id: str) -> Path:
        return record_dir / f"{file_id}-cc.csv"

    @staticmethod
    def _results_dest(record_dir: Path, file_id: str) -> Path:
        return record_dir / f"{file_id}-results.csv"

    def _maybe_copy_force(
        self,
        src: Path,
        dest: Path,
        force_paths: list[str],
    ) -> None:
        if not src.exists():
            return
        self._copy_overwrite(src, dest)
        force_paths.append(str(dest))

    @staticmethod
    def _normalize_stem(stem: str) -> str:
        without_cc = _CC_PREFIX_RE.sub("", stem)
        return _MEASUREMENT_SUFFIX_RE.sub("", without_cc)

    @staticmethod
    def _is_measurement(stem: str) -> bool:
        return _MEASUREMENT_SUFFIX_RE.search(stem) is not None

    @staticmethod
    def _is_cc(stem: str) -> bool:
        return stem.lower().startswith("cc_")

    @staticmethod
    def _copy_overwrite(src: Path, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(src, dest)
        except shutil.SameFileError:
            return

    def _runtime_id_separator(self) -> str:
        return self._id_separator or "-"
