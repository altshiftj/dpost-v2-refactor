"""Processor for Hioki analyzer exports (CSV + Excel)."""
from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Optional

from ipat_watchdog.core.config.schema import DeviceConfig
from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.core.processing.file_processor_abstract import (
    FileProcessorABS,
    FileProbeResult,
    ProcessingOutput,
)
from ipat_watchdog.core.records.local_record import LocalRecord
from ipat_watchdog.core.storage.filesystem_utils import get_unique_filename, move_item

logger = setup_logger(__name__)

_MEASUREMENT_SUFFIX_RE = re.compile(r"_(\d{14})$")
_CC_PREFIX_RE = re.compile(r"^cc_", re.IGNORECASE)


class FileProcessorHioki(FileProcessorABS):
    """Handle Hioki CSV outputs plus optional Excel exports."""

    def __init__(self, device_config: DeviceConfig) -> None:
        super().__init__(device_config)
        self.device_config = device_config

    # No staging/pairing needed
    def device_specific_preprocessing(self, path: str) -> Optional[str]:
        candidate = Path(path)
        if candidate.suffix.lower() != ".csv":
            return path

        normalized = self._normalize_stem(candidate.stem)
        if normalized != candidate.stem:
            return str(candidate.with_name(f"{normalized}{candidate.suffix}"))
        return path

    # Probe: rely on extension
    def probe_file(self, filepath: str) -> FileProbeResult:
        p = Path(filepath)
        ext = p.suffix.lower()

        # Adjust exported_extensions vs allowed_extensions according to your config
        if ext in self.device_config.files.exported_extensions:
            return FileProbeResult.match(
                confidence=0.6,
                reason="Excel export for Hioki analyzer",
            )
        return FileProbeResult.mismatch("Unsupported extension for Hioki (Excel expected)")

    def is_appendable(self, record: LocalRecord, filename_prefix: str, extension: str) -> bool:
        # allow multiple exports in the same record
        return True

    @classmethod
    def get_device_id(cls) -> str:
        return "hioki_blb"

    def device_specific_processing(
        self,
        src_path: str,
        record_path: str,
        filename_prefix: str,
        extension: str,
    ) -> ProcessingOutput:
        """
        - Measurement CSVs: move to a unique file_id-based name.
        - CC CSV: overwrite `<file_id>-cc.csv` and force-upload.
        - Aggregate CSV: overwrite `<file_id>-results.csv` and force-upload.
        - Excel exports: keep the historical move-only behaviour.
        """
        src = Path(src_path)
        record_dir = Path(record_path)
        record_dir.mkdir(parents=True, exist_ok=True)
        ext = src.suffix.lower() or extension.lower()

        if ext in {".xlsx", ".xls"}:
            destination = get_unique_filename(record_path, filename_prefix, ext)
            move_item(src_path, destination)
            return ProcessingOutput(final_path=destination, datatype="hioki")

        if ext != ".csv":
            destination = get_unique_filename(record_path, filename_prefix, ext)
            move_item(src_path, destination)
            return ProcessingOutput(final_path=destination, datatype="hioki")

        stem = src.stem
        base = self._normalize_stem(stem)
        force_paths: list[str] = []

        if self._is_measurement(stem):
            destination = get_unique_filename(record_path, filename_prefix, ext)
            move_item(src_path, destination)

            cc_src = src.parent / f"CC_{base}.csv"
            cc_dest = record_dir / f"{filename_prefix}-cc.csv"
            if cc_src.exists():
                self._copy_overwrite(cc_src, cc_dest)
                force_paths.append(str(cc_dest))

            agg_src = src.parent / f"{base}.csv"
            agg_dest = record_dir / f"{filename_prefix}-results.csv"
            if agg_src.exists():
                self._copy_overwrite(agg_src, agg_dest)
                force_paths.append(str(agg_dest))

            return ProcessingOutput(
                final_path=destination,
                datatype="hioki",
                force_paths=tuple(force_paths),
            )

        if self._is_cc(stem):
            cc_dest = record_dir / f"{filename_prefix}-cc.csv"
            self._copy_overwrite(src, cc_dest)
            force_paths.append(str(cc_dest))
            return ProcessingOutput(
                final_path=str(cc_dest),
                datatype="hioki",
                force_paths=tuple(force_paths),
            )

        agg_dest = record_dir / f"{filename_prefix}-results.csv"
        self._copy_overwrite(src, agg_dest)
        force_paths.append(str(agg_dest))
        return ProcessingOutput(
            final_path=str(agg_dest),
            datatype="hioki",
            force_paths=tuple(force_paths),
        )

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
