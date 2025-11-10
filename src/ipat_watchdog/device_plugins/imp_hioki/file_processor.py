"""Processor for Hioki analyzer exports (Excel only)."""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import os, re
from ipat_watchdog.core.config import constants as _CONST
from ipat_watchdog.core.config import current
from ipat_watchdog.core.config.schema import DeviceConfig
from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.core.processing.file_processor_abstract import (
    FileProcessorABS, FileProbeResult, ProcessingOutput,
)
from ipat_watchdog.core.records.local_record import LocalRecord
from ipat_watchdog.core.storage.filesystem_utils import get_unique_filename, move_item

logger = setup_logger(__name__)

def _id_separator() -> str:
    try:
        return current().id_separator
    except RuntimeError:
        return _CONST.ID_SEP

class FileProcessorHioki(FileProcessorABS):
    """Export-only: move Excel workbook into the record with a unique name."""

    def __init__(self, device_config: DeviceConfig) -> None:
        super().__init__(device_config)
        self.device_config = device_config

    # No staging/pairing needed
    def device_specific_preprocessing(self, path: str) -> Optional[str]:
        return path

    # Probe: rely on extension; Excel is a binary container -> return unknown
    def probe_file(self, filepath: str) -> FileProbeResult:
        p = Path(filepath)
        ext = p.suffix.lower()
        if ext not in self.device_config.files.exported_extensions:
            return FileProbeResult.mismatch("Unsupported extension for Hioki (Excel expected)")
        return FileProbeResult.unknown("Excel export (binary); routed by extension")

    def is_appendable(self, record: LocalRecord, filename_prefix: str, extension: str) -> bool:
        return True  # allow multiple exports in same record

    @classmethod
    def get_device_id(cls) -> str:
        return "hioki_blb"

    def device_specific_processing(
        
        self, src_path: str, record_path: str, filename_prefix: str, extension: str
    ) -> ProcessingOutput:
        src = Path(src_path)
        ext = src.suffix.lower()

        # 1) derive base + kind from the source name
    #    e.g. CC_1m_min.xlsx        -> base="1m_min", kind="config"
    #         1m_min_20251022114140 -> base="1m_min", kind="raw"
    #         1m_min                -> base="1m_min", kind="aggregate"
        TS_RE = re.compile(r"_(?P<ts>\d{14})$", re.ASCII)
        stem = src.stem
        if stem.startswith("CC_"):
           base, ts, kind = stem[3:], None, "config"
        else:
           m = TS_RE.search(stem)
        if m:
            base, ts, kind = stem[:m.start()], m.group("ts"), "raw"
        else:
            base, ts, kind = stem, None, "aggregate"

        # 2) compose the final stem as <user>-<institute>-<base>
    #    (read from env, or fall back to your global defaults)
        user = os.getenv("WATCHDOG_USER", "user")
        inst = os.getenv("WATCHDOG_INSTITUTE", "inst")
        final_stem = f"{user}-{inst}-{base}"  # -> jfi-ipat-cc_current_sweep
        PAT = re.compile(r"^[A-Za-z0-9]{3,}-[A-Za-z0-9]{3,}-[A-Za-z0-9_]+$")

            # 3) build the destination path with that stem (no extra suffixes)
        dest = Path(record_path) / f"{final_stem}{ext}"

    # keep collision safety (if a file already exists, get a unique variant)
        if dest.exists():
          dest = Path(get_unique_filename(record_path, final_stem, ext))

          logger.info("Hioki export: %s -> %s", src, dest)
          move_item(str(src), str(dest))
          #Optional stricter check. If rejecting names won’t become valid after stripping 
          # (e.g., bad base), add this just before moving
        if not PAT.match(final_stem):
            # route to To_Rename using your existing helper if you have one
            from ipat_watchdog.core.storage.filesystem_utils import move_to_exception_folder
            logger.warning("Final stem '%s' invalid; sending to To_Rename", final_stem)
            move_to_exception_folder(str(src))

        return ProcessingOutput(final_path=str(dest), datatype="hioki")
