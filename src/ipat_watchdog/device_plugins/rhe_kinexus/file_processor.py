"""Processor for Kinexus Pro+ rheometer native + export artefacts."""

from __future__ import annotations

import time
import zipfile
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Deque, Dict, List, Optional

from ipat_watchdog.core.config import constants as _CONST
from ipat_watchdog.core.config import current
from ipat_watchdog.core.config.schema import DeviceConfig
from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.core.processing.batch_models import ExportRawPair as _Pair
from ipat_watchdog.core.processing.batch_models import FlushBatch as _FlushBatch
from ipat_watchdog.core.processing.batch_models import PendingPath as _PendingRaw
from ipat_watchdog.core.processing.file_processor_abstract import (
    FileProbeResult,
    FileProcessorABS,
    PreprocessingResult,
    ProcessingOutput,
)
from ipat_watchdog.core.processing.staging_utils import (
    create_unique_stage_dir,
    find_stale_stage_dirs,
    reconstruct_pairs_from_stage,
)
from ipat_watchdog.core.processing.text_utils import read_text_prefix
from ipat_watchdog.core.records.local_record import LocalRecord
from ipat_watchdog.core.storage.filesystem_utils import (
    get_unique_filename,
    move_item,
    move_to_exception_folder,
)

logger = setup_logger(__name__)


def _id_separator() -> str:
    try:
        return current().id_separator
    except RuntimeError:
        return _CONST.ID_SEP


@dataclass
class _Sentinel:
    export_path: Path
    prefix: str
    created: float


@dataclass
class _FolderState:
    pending_raw: Deque[_PendingRaw] = field(default_factory=deque)
    bucket: List[_Pair] = field(default_factory=list)
    sentinel: Optional[_Sentinel] = None

    def is_idle(self) -> bool:
        return not self.pending_raw and not self.bucket and self.sentinel is None


class FileProcessorRHEKinexus(FileProcessorABS):
    """Sentinel-driven pairing of Kinexus native `.rdf` files and exports."""

    def __init__(self, device_config: DeviceConfig) -> None:
        super().__init__(device_config)
        self.device_config = device_config
        self._state: Dict[str, _FolderState] = {}
        self._finalizing: Dict[str, _FlushBatch] = {}
        self._raw_to_stage: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Pre-processing (sentinel sequencing + staging)
    # ------------------------------------------------------------------
    def device_specific_preprocessing(self, path: str) -> Optional[PreprocessingResult]:
        element = Path(path)
        logger.debug("Kinexus: preprocessing path=%s", element)

        staged = self._raw_to_stage.get(str(element))
        if staged:
            return PreprocessingResult.passthrough(staged)
        if not element.exists():
            return None

        folder_key = str(element.parent.resolve())
        state = self._state.setdefault(folder_key, _FolderState())

        result: Optional[PreprocessingResult] = None
        if self._is_export(element):
            result = self._handle_export(folder_key, state, element)
        elif self._is_native(element):
            result = self._handle_native(folder_key, state, element)
        else:
            logger.debug("Kinexus: ignoring non-native/export file %s", element)

        self._purge_stale()
        return result

    def _handle_export(
        self, folder_key: str, state: _FolderState, path: Path
    ) -> Optional[PreprocessingResult]:
        if self._is_export_finalizing(path):
            return None
        if self._export_tracked(state, path):
            return None

        prefix = path.stem

        if state.pending_raw:
            pending = state.pending_raw.popleft()
            state.bucket.append(
                _Pair(export_path=path, raw_path=pending.path, created=time.time())
            )
            logger.debug(
                "Kinexus: paired export %s with pending native %s", path, pending.path
            )
            return None

        sentinel = state.sentinel
        if sentinel and sentinel.export_path != path:
            logger.warning(
                "Kinexus: replacing pending sentinel %s with %s",
                sentinel.export_path,
                path,
            )

        state.sentinel = _Sentinel(export_path=path, prefix=prefix, created=time.time())
        logger.debug(
            "Kinexus: remembered sentinel export %s with prefix=%r", path, prefix
        )
        return None

    def _handle_native(
        self, folder_key: str, state: _FolderState, path: Path
    ) -> Optional[PreprocessingResult]:
        staged = self._raw_to_stage.get(str(path))
        if staged:
            return PreprocessingResult.passthrough(staged)
        if self._raw_tracked(state, path):
            return None

        sentinel = state.sentinel
        if sentinel is not None:
            batch_pairs = list(state.bucket)
            batch_pairs.append(
                _Pair(
                    export_path=sentinel.export_path, raw_path=path, created=time.time()
                )
            )
            # Use the native (.rdf) stem as the authoritative batch prefix
            native_prefix = path.stem
            stage_dir = self._create_unique_stage_dir(path.parent, native_prefix)

            relocated_pairs: List[_Pair] = []
            for pair in batch_pairs:
                orig_export = pair.export_path
                orig_raw = pair.raw_path
                new_export = stage_dir / orig_export.name
                new_raw = stage_dir / orig_raw.name
                try:
                    if orig_export.exists():
                        move_item(str(orig_export), str(new_export))
                    if orig_raw.exists():
                        move_item(str(orig_raw), str(new_raw))
                except Exception:
                    logger.exception(
                        "Kinexus: failed staging pair (%s, %s) into %s",
                        orig_export,
                        orig_raw,
                        stage_dir,
                    )
                relocated_pairs.append(
                    _Pair(
                        export_path=new_export, raw_path=new_raw, created=pair.created
                    )
                )
                self._raw_to_stage[str(orig_raw)] = str(stage_dir)

            staged_batch = _FlushBatch(prefix=native_prefix, pairs=relocated_pairs)
            self._finalizing[str(stage_dir)] = staged_batch

            logger.debug(
                "Kinexus: sentinel native %s triggered flush; staged %d pairs in %s (prefix=%r)",
                path,
                len(staged_batch.pairs),
                stage_dir,
                staged_batch.prefix,
            )

            state.bucket.clear()
            state.pending_raw.clear()
            state.sentinel = None
            self._cleanup_state(folder_key)
            return PreprocessingResult.passthrough(str(stage_dir))

        state.pending_raw.append(_PendingRaw(path=path, created=time.time()))
        logger.debug("Kinexus: remembered native %s awaiting export", path)
        return None

    # ------------------------------------------------------------------
    # Probing (CSV content heuristics)
    # ------------------------------------------------------------------
    def probe_file(self, filepath: str) -> FileProbeResult:
        path = Path(filepath)
        ext = path.suffix.lower()
        native_exts = self.device_config.files.native_extensions
        exported_exts = self.device_config.files.exported_extensions

        if ext in native_exts:
            return FileProbeResult.unknown("Binary native file; probe skipped")

        if ext not in exported_exts:
            return FileProbeResult.mismatch("Unsupported extension for Kinexus")

        try:
            snippet = read_text_prefix(
                path,
                encodings=("utf-8-sig", "utf-8", "latin-1", "cp1252"),
                errors="ignore",
            )
        except Exception as exc:  # pragma: no cover
            logger.debug("Kinexus probe read failed '%s': %s", path, exc)
            return FileProbeResult.unknown(str(exc))

        text = snippet.lower()
        positives = ["kinexus", "rspace", "netzsch", "malvern", "viscosity", "g'", 'g"']
        negatives = ["dissolution", "zwick", "ut m", "la-960", "partica"]

        score = sum(1 for t in positives if t in text) - sum(
            1 for t in negatives if t in text
        )
        if score <= 0:
            return FileProbeResult.unknown("CSV content inconclusive for Kinexus")

        confidence = min(0.55 + 0.15 * score, 0.95)
        return FileProbeResult.match(
            confidence=confidence, reason=f"Found Kinexus markers (score={score})"
        )

    def is_appendable(
        self, record: LocalRecord, filename_prefix: str, extension: str
    ) -> bool:
        return True

    @classmethod
    def get_device_id(cls) -> str:
        return "rhe_kinexus"

    # ------------------------------------------------------------------
    # Processing (sequential numbering per sentinel prefix)
    # ------------------------------------------------------------------
    def device_specific_processing(
        self,
        src_path: str,
        record_path: str,
        filename_prefix: str,
        extension: str,
    ) -> ProcessingOutput:
        src = Path(src_path)
        if src.is_dir():
            batch = self._finalizing.pop(str(src), None)
            if batch is None:
                batch = self._reconstruct_batch_from_stage(src)
        else:
            batch = self._finalizing.pop(str(src), None)
            if batch is None:
                raise RuntimeError("No pending batch for this item; cannot finalize")

        record_dir = Path(record_path)
        record_dir.mkdir(parents=True, exist_ok=True)

        base_prefix = filename_prefix or batch.prefix
        logger.debug(
            "Kinexus: processing src=%s record_dir=%s base_prefix=%r pairs=%d",
            src,
            record_dir,
            base_prefix,
            len(batch.pairs),
        )

        processed = 0
        for pair in batch.pairs:
            if not pair.export_path.exists():
                raise RuntimeError(f"Expected export missing: {pair.export_path}")
            if not pair.raw_path.exists():
                raise RuntimeError(f"Expected native missing: {pair.raw_path}")
            # Use global sequencing helper for consistent -NN numbering.
            unique_export_path = Path(
                get_unique_filename(
                    str(record_dir), base_prefix, pair.export_path.suffix.lower()
                )
            )
            basename = unique_export_path.stem
            move_item(str(pair.export_path), str(unique_export_path))
            logger.debug(
                "Kinexus: export moved %s -> %s", pair.export_path, unique_export_path
            )

            zip_dest = record_dir / f"{basename}.zip"
            arcname = f"{basename}{pair.raw_path.suffix.lower()}"
            self._zip_raw(pair.raw_path, zip_dest, arcname)
            logger.debug(
                "Kinexus: native zipped %s -> %s (arcname=%s)",
                pair.raw_path,
                zip_dest,
                arcname,
            )
            processed += 1

        if src.is_dir():
            try:
                if not any(src.iterdir()):
                    src.rmdir()
            except Exception:
                pass
            try:
                for key, value in list(self._raw_to_stage.items()):
                    if value == str(src):
                        self._raw_to_stage.pop(key, None)
            except Exception:
                pass

        logger.debug(
            "Kinexus: finalized %d pair(s) for prefix=%r", processed, base_prefix
        )
        return ProcessingOutput(final_path=str(record_dir), datatype="rhe")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _is_native(self, path: Path) -> bool:
        native_exts = getattr(self.device_config.files, "native_extensions", [])
        return path.suffix.lower() in {ext.lower() for ext in native_exts}

    def _is_export(self, path: Path) -> bool:
        export_exts = getattr(self.device_config.files, "exported_extensions", [])
        return path.suffix.lower() in {ext.lower() for ext in export_exts}

    def _export_tracked(self, state: _FolderState, path: Path) -> bool:
        if state.sentinel and state.sentinel.export_path == path:
            return True
        return any(pair.export_path == path for pair in state.bucket)

    def _is_export_finalizing(self, path: Path) -> bool:
        target = str(path)
        for batch in self._finalizing.values():
            if any(str(pair.export_path) == target for pair in batch.pairs):
                return True
        return False

    def _raw_tracked(self, state: _FolderState, path: Path) -> bool:
        return any(pair.raw_path == path for pair in state.bucket) or any(
            pending.path == path for pending in state.pending_raw
        )

    def _cleanup_state(self, folder_key: str) -> None:
        state = self._state.get(folder_key)
        if state and state.is_idle():
            self._state.pop(folder_key, None)

    def _next_sequence_basename(self, directory: Path, prefix: str) -> str:
        sep = _id_separator()
        max_index = 0
        for existing in directory.iterdir():
            if not existing.is_file():
                continue
            stem = existing.stem
            parts = stem.rsplit(sep, 1)
            if len(parts) != 2:
                continue
            base, suffix = parts
            if base != prefix:
                continue
            try:
                idx = int(suffix)
            except ValueError:
                continue
            max_index = max(max_index, idx)
        next_name = f"{prefix}{sep}{max_index + 1:02d}"
        logger.debug(
            "Kinexus: next sequence for prefix=%r in %s -> %s",
            prefix,
            directory,
            next_name,
        )
        return next_name

    @staticmethod
    def _zip_raw(src: Path, dest: Path, arcname: str) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(dest, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(src, arcname=arcname)
        try:
            src.unlink(missing_ok=True)
        except Exception:
            pass

    def _purge_stale(self) -> None:
        now = time.time()
        ttl = getattr(getattr(self.device_config, "batch", None), "ttl_seconds", 600)

        folder_keys = list(self._state.keys())
        for folder_key in folder_keys:
            state = self._state.get(folder_key)
            if state is None:
                continue

            refreshed_pending: Deque[_PendingRaw] = deque()
            for pending in list(state.pending_raw):
                if now - pending.created > ttl:
                    if pending.path.exists():
                        try:
                            move_to_exception_folder(str(pending.path))
                            logger.info(
                                "Kinexus: moved stale pending native '%s' to exception",
                                pending.path,
                            )
                        except Exception:
                            logger.exception(
                                "Kinexus: failed moving stale pending native %s",
                                pending.path,
                            )
                else:
                    refreshed_pending.append(pending)
            state.pending_raw = refreshed_pending

            refreshed_bucket: List[_Pair] = []
            for pair in list(state.bucket):
                if now - pair.created > ttl:
                    for component, label in (
                        (pair.export_path, "export"),
                        (pair.raw_path, "native"),
                    ):
                        if component.exists():
                            try:
                                move_to_exception_folder(str(component))
                                logger.info(
                                    "Kinexus: moved stale queued %s '%s' to exception",
                                    label,
                                    component,
                                )
                            except Exception:
                                logger.exception(
                                    "Kinexus: failed moving stale %s %s",
                                    label,
                                    component,
                                )
                else:
                    refreshed_bucket.append(pair)
            state.bucket = refreshed_bucket

            sentinel = state.sentinel
            if sentinel and now - sentinel.created > ttl:
                if sentinel.export_path.exists():
                    try:
                        move_to_exception_folder(str(sentinel.export_path))
                        logger.info(
                            "Kinexus: moved stale sentinel export '%s' to exception",
                            sentinel.export_path,
                        )
                    except Exception:
                        logger.exception(
                            "Kinexus: failed moving stale sentinel %s",
                            sentinel.export_path,
                        )
                state.sentinel = None

            self._cleanup_state(folder_key)

        for folder_key in folder_keys:
            parent = Path(folder_key)
            try:
                stale_dirs = find_stale_stage_dirs(
                    parent,
                    marker=".__staged__",
                    ttl_seconds=ttl,
                    now=now,
                    active=self._finalizing.keys(),
                )
                for child in stale_dirs:
                    try:
                        move_to_exception_folder(str(child))
                        logger.info(
                            "Kinexus: moved stale staging folder '%s' to exception",
                            child,
                        )
                        for key, value in list(self._raw_to_stage.items()):
                            if value == str(child):
                                self._raw_to_stage.pop(key, None)
                    except Exception:
                        logger.exception(
                            "Kinexus: failed moving stale staging folder %s",
                            child,
                        )
            except Exception:
                continue

    def _create_unique_stage_dir(self, base_dir: Path, prefix: str) -> Path:
        return create_unique_stage_dir(
            base_dir, prefix, marker=".__staged__", max_index=1000
        )

    def _reconstruct_batch_from_stage(self, stage_dir: Path) -> _FlushBatch:
        prefix, pairs = reconstruct_pairs_from_stage(
            stage_dir,
            self._is_export,
            self._is_native,
            marker=".__staged__",
            left_label="export",
            right_label="native",
        )
        staged_pairs: List[_Pair] = []
        for export_path, raw_path in pairs:
            staged_pairs.append(
                _Pair(export_path=export_path, raw_path=raw_path, created=time.time())
            )
        return _FlushBatch(prefix=prefix, pairs=staged_pairs)
