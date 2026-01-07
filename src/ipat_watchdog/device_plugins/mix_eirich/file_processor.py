"""File processor for Eirich mixer text exports."""

from __future__ import annotations

from fnmatch import fnmatch
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


class FileProcessorEirich(FileProcessorABS):
    """Moves .txt exports from the Eirich mixer into the record folder."""

    def __init__(self, device_config: DeviceConfig) -> None:
        super().__init__(device_config)
        self.device_config = device_config

    # No staging/pairing needed for simple text exports
    def device_specific_preprocessing(self, path: str) -> Optional[str]:
        return path

    def probe_file(self, filepath: str) -> FileProbeResult:
        """
        Identify Eirich mixer files by content fingerprinting.
        
        Uses column header markers and filename patterns to compute confidence.
        """
        path = Path(filepath)
        ext = path.suffix.lower()
        exported_exts = self.device_config.files.exported_extensions

        if ext not in exported_exts:
            return FileProbeResult.mismatch(f"Unsupported extension for Eirich mixer: {ext}")

        # Try reading file content
        try:
            snippet = self._read_text_prefix(path)
        except Exception as exc:
            logger.debug("Eirich probe failed to read '%s': %s", path, exc)
            return FileProbeResult.unknown(str(exc))

        # Count positive marker hits (case-insensitive)
        text = snippet.lower()
        markers = self.device_config.markers
        positive_hits = sum(1 for marker in markers.positive if marker in text)

        # Check filename pattern bonus
        filename_bonus = 1 if self._matches_filename_pattern(filepath) else 0

        # Compute total score
        score = positive_hits + filename_bonus

        if score <= 0:
            return FileProbeResult.unknown("No Eirich markers found")

        # Calculate confidence: base + (per_hit * score), capped at max
        confidence = min(
            markers.base_confidence + markers.confidence_per_hit * score,
            markers.max_confidence
        )

        return FileProbeResult.match(
            confidence=confidence,
            reason=f"Found {positive_hits} Eirich markers + {filename_bonus} filename match"
        )

    def is_appendable(self, record: LocalRecord, filename_prefix: str, extension: str) -> bool:
        # Allow multiple .txt exports within the same record
        return True

    @classmethod
    def get_device_id(cls) -> str:
        """
        Device ID used by the processor factory.

        This should match the identifier you use in the config, e.g. 'mix_eirich'.
        """
        return "mix_eirich"

    def device_specific_processing(
        self,
        src_path: str,
        record_path: str,
        filename_prefix: str,
        extension: str,
    ) -> ProcessingOutput:
        """
        Mirror EXTR/Hioki behaviour: use the already-validated filename_prefix
        and let filesystem_utils generate a unique name in the record folder.
        """
        destination = get_unique_filename(record_path, filename_prefix, extension)
        move_item(src_path, destination)

        # You can change 'datatype' to something more specific if you like,
        # e.g. 'mix_eirich'; for now it's fine to keep 'tabular' or 'text'.
        return ProcessingOutput(final_path=destination, datatype="tabular")

    @staticmethod
    def _read_text_prefix(path: Path, bytes_limit: int = 4096) -> str:
        """Read and decode the first bytes of a text export safely."""
        raw = Path(path).read_bytes()[:bytes_limit]
        for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw.decode("latin-1", errors="ignore")

    def _matches_filename_pattern(self, filepath: str) -> bool:
        """Check if filename matches any configured Eirich naming patterns."""
        filename = Path(filepath).name.lower()
        patterns = self.device_config.markers.filename_patterns
        
        return any(fnmatch(filename, pattern.lower()) for pattern in patterns)
