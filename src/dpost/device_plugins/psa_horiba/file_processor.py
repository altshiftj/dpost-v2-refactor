"""Processor for PSA HORIBA staged CSV/NGB pairing under canonical dpost namespace."""

from __future__ import annotations

import re
import time
import zipfile
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Deque, Dict, List, Optional

from dpost.application.config import DeviceConfig
from dpost.application.processing.error_handling import safe_move_to_exception
from dpost.application.processing.file_processor_abstract import (
    FileProbeResult,
    FileProcessorABS,
    PreprocessingResult,
    ProcessingOutput,
)
from dpost.domain.processing.batch_models import CsvNgbPair as _Pair
from dpost.domain.processing.batch_models import FlushBatch as _FlushBatch
from dpost.domain.processing.batch_models import PendingPath as _PendingNGB
from dpost.domain.processing.staging import (
    find_stale_stage_dirs,
    reconstruct_pairs_from_stage,
)
from dpost.domain.processing.text import read_text_prefix
from dpost.domain.records.local_record import LocalRecord
from dpost.infrastructure.logging import setup_logger
from dpost.infrastructure.storage.filesystem_utils import move_item
from dpost.infrastructure.storage.staging_dirs import create_unique_stage_dir

logger = setup_logger(__name__)

_PROBENAME_KEY = "probenname"
_MAX_PREFIX_BYTES = 200_000


def _runtime_id_separator() -> str:
    from dpost.application.config import current

    return current().id_separator


def _is_ngb(path: Path) -> bool:
    return path.suffix.lower() == ".ngb"


def _is_csv_like(path: Path) -> bool:
    return path.suffix.lower() in {".csv", ".tsv"}


@dataclass
class _Sentinel:
    csv_path: Path
    prefix: str
    raw_probenname: str
    created: float


@dataclass
class _FolderState:
    pending_ngb: Deque[_PendingNGB] = field(default_factory=deque)
    bucket: List[_Pair] = field(default_factory=list)
    sentinel: Optional[_Sentinel] = None

    def is_idle(self) -> bool:
        return not self.pending_ngb and not self.bucket and self.sentinel is None


class FileProcessorPSAHoriba(FileProcessorABS):
    """Bucket NGB/CSV pairs and flush them on sentinel sequence completion."""

    def __init__(
        self,
        device_config: DeviceConfig,
        id_separator: str | None = None,
    ) -> None:
        super().__init__(device_config)
        self.device_config = device_config
        self._id_separator = id_separator
        self._state: Dict[str, _FolderState] = {}
        self._finalizing: Dict[str, _FlushBatch] = {}
        self._ngb_to_stage: Dict[str, str] = {}

    def configure_runtime_context(
        self,
        *,
        id_separator: str | None = None,
        filename_pattern=None,
    ) -> None:
        """Capture runtime separator when constructed without explicit override."""
        if self._id_separator is None and id_separator is not None:
            self._id_separator = id_separator

    def device_specific_preprocessing(self, path: str) -> Optional[PreprocessingResult]:
        item = Path(path)
        logger.debug("PSA: preprocessing path=%s", item)
        staged = self._ngb_to_stage.get(str(item))
        if staged:
            return PreprocessingResult.passthrough(staged)
        if not item.exists():
            return None

        folder_key = str(item.parent.resolve())
        state = self._state.get(folder_key)
        if state is None:
            state = _FolderState()
            self._state[folder_key] = state

        if _is_csv_like(item):
            result = self._handle_csv(folder_key, state, item)
            self._purge_stale()
            return result

        if _is_ngb(item):
            result = self._handle_ngb(folder_key, state, item)
            self._purge_stale()
            return result

        logger.debug("PSA: ignoring non CSV/NGB file %s", item)
        return None

    def _handle_csv(
        self, folder_key: str, state: _FolderState, path: Path
    ) -> Optional[PreprocessingResult]:
        if self._is_csv_finalizing(path):
            return None
        if self._csv_tracked(state, path):
            return None

        try:
            meta = self._parse_csv_metadata(path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("PSA: CSV metadata parse failed for %s: %s", path, exc)
            meta = {}

        raw_probenname = (meta.get(_PROBENAME_KEY) or "").strip()
        prefix = raw_probenname

        if state.pending_ngb:
            pending = state.pending_ngb.popleft()
            state.bucket.append(
                _Pair(csv_path=path, ngb_path=pending.path, created=time.time())
            )
            logger.debug(
                "PSA: queued bucket pair CSV %s with NGB %s (prefix hint %r)",
                path,
                pending.path,
                prefix,
            )
            return None

        sentinel = state.sentinel
        if sentinel and sentinel.csv_path != path:
            logger.warning(
                "PSA: replacing pending sentinel CSV %s with new sentinel %s",
                sentinel.csv_path,
                path,
            )

        state.sentinel = _Sentinel(
            csv_path=path,
            prefix=prefix,
            raw_probenname=raw_probenname,
            created=time.time(),
        )
        logger.debug("PSA: remembered sentinel CSV %s with prefix=%r", path, prefix)
        return None

    def _handle_ngb(
        self, folder_key: str, state: _FolderState, path: Path
    ) -> Optional[PreprocessingResult]:
        staged = self._ngb_to_stage.get(str(path))
        if staged:
            return PreprocessingResult.passthrough(staged)
        if self._ngb_tracked(state, path):
            return None

        sentinel = state.sentinel
        if sentinel is not None:
            batch_pairs = list(state.bucket)
            batch_pairs.append(
                _Pair(csv_path=sentinel.csv_path, ngb_path=path, created=time.time())
            )

            batch = _FlushBatch(
                prefix=sentinel.prefix,
                raw_probenname=sentinel.raw_probenname,
                pairs=batch_pairs,
            )
            stage_dir = self._create_unique_stage_dir(path.parent, sentinel.prefix)

            relocated_pairs: List[_Pair] = []
            for pair in batch.pairs:
                new_csv = stage_dir / pair.csv_path.name
                new_ngb = stage_dir / pair.ngb_path.name
                try:
                    if pair.csv_path.exists():
                        move_item(pair.csv_path, new_csv)
                    if pair.ngb_path.exists():
                        move_item(pair.ngb_path, new_ngb)
                except Exception:  # noqa: BLE001
                    logger.exception(
                        "PSA: failed staging pair (%s, %s) into %s",
                        pair.csv_path,
                        pair.ngb_path,
                        stage_dir,
                    )
                relocated_pairs.append(
                    _Pair(csv_path=new_csv, ngb_path=new_ngb, created=pair.created)
                )

            staged_batch = _FlushBatch(
                prefix=batch.prefix,
                raw_probenname=batch.raw_probenname,
                pairs=relocated_pairs,
            )
            self._finalizing[str(stage_dir)] = staged_batch
            self._ngb_to_stage[str(path)] = str(stage_dir)

            logger.debug(
                "PSA: sentinel NGB %s triggered flush; staged %d pairs in %s using prefix=%r",
                path,
                len(staged_batch.pairs),
                stage_dir,
                staged_batch.prefix,
            )

            state.bucket.clear()
            state.pending_ngb.clear()
            state.sentinel = None
            self._cleanup_state(folder_key)
            return PreprocessingResult.passthrough(str(stage_dir))

        state.pending_ngb.append(_PendingNGB(path=path, created=time.time()))
        logger.debug("PSA: remembered NGB %s awaiting CSV", path)
        return None

    def probe_file(self, filepath: str) -> FileProbeResult:
        path = Path(filepath)
        if not _is_csv_like(path):
            return FileProbeResult.mismatch("Not a CSV/TSV for PSA Horiba")
        try:
            text = read_text_prefix(
                path,
                encodings=("utf-8-sig", "utf-8", "cp1252", "latin-1"),
                errors=None,
                fallback_encoding="latin-1",
                fallback_errors="ignore",
                logger=logger,
                log_label="PSA",
            )
        except Exception as exc:  # noqa: BLE001
            return FileProbeResult.unknown(str(exc))
        lowered = text.lower()
        score = sum(
            token in lowered for token in ["horiba", "partica", "la-960", "diameter"]
        ) - sum(token in lowered for token in ["dissolution", "cumulative release"])
        if score <= 0:
            return FileProbeResult.unknown("Content inconclusive for PSA Horiba")
        confidence = min(0.55 + 0.15 * score, 0.95)
        return FileProbeResult.match(
            confidence=confidence, reason=f"PSA markers (score={score})"
        )

    def is_appendable(
        self, record: LocalRecord, filename_prefix: str, extension: str
    ) -> bool:
        return True

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
            "PSA: processing start src=%s record_dir=%s base_prefix=%r pairs=%d",
            src,
            record_dir,
            base_prefix,
            len(batch.pairs),
        )
        if base_prefix != batch.prefix:
            logger.debug(
                "PSA: filename prefix %r differs from sentinel prefix %r; using %r",
                filename_prefix,
                batch.prefix,
                base_prefix,
            )

        processed_pairs = 0
        for pair in batch.pairs:
            if not pair.csv_path.exists():
                raise RuntimeError(
                    f"Expected CSV missing before processing: {pair.csv_path}"
                )
            if not pair.ngb_path.exists():
                raise RuntimeError(
                    f"Expected NGB missing before processing: {pair.ngb_path}"
                )

            basename = self._next_sequence_basename(record_dir, base_prefix)
            csv_dest = record_dir / f"{basename}.csv"
            move_item(pair.csv_path, csv_dest)
            logger.debug("PSA: CSV moved %s -> %s", pair.csv_path, csv_dest)

            zip_dest = record_dir / f"{basename}.zip"
            arcname = f"{basename}.ngb"
            self._zip_ngb(pair.ngb_path, zip_dest, arcname)
            logger.debug(
                "PSA: NGB zipped %s -> %s (arcname=%s)",
                pair.ngb_path,
                zip_dest,
                arcname,
            )
            processed_pairs += 1

        logger.debug(
            "PSA: finalised %d pair(s) for prefix=%r (raw probenname=%r)",
            processed_pairs,
            base_prefix,
            batch.raw_probenname,
        )

        if src.is_dir():
            try:
                remaining = list(src.iterdir())
                if not remaining:
                    src.rmdir()
            except Exception:  # noqa: BLE001
                pass
            try:
                for key, value in list(self._ngb_to_stage.items()):
                    if value == str(src):
                        self._ngb_to_stage.pop(key, None)
            except Exception:  # noqa: BLE001
                pass

        return ProcessingOutput(final_path=str(record_dir), datatype="psa")

    def _csv_tracked(self, state: _FolderState, path: Path) -> bool:
        if state.sentinel and state.sentinel.csv_path == path:
            return True
        return any(pair.csv_path == path for pair in state.bucket)

    def _is_csv_finalizing(self, path: Path) -> bool:
        target = str(path)
        for batch in self._finalizing.values():
            if any(str(pair.csv_path) == target for pair in batch.pairs):
                return True
        return False

    def _ngb_tracked(self, state: _FolderState, path: Path) -> bool:
        if state.sentinel and state.sentinel.csv_path == path:
            return False
        return any(pair.ngb_path == path for pair in state.bucket) or any(
            pending.path == path for pending in state.pending_ngb
        )

    def _cleanup_state(self, folder_key: str) -> None:
        state = self._state.get(folder_key)
        if state and state.is_idle():
            self._state.pop(folder_key, None)

    def _next_sequence_basename(self, directory: Path, prefix: str) -> str:
        sep = self._resolve_id_separator()
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
            "PSA: next sequence for prefix=%r in %s -> %s", prefix, directory, next_name
        )
        return next_name

    def _resolve_id_separator(self) -> str:
        if self._id_separator is not None:
            return self._id_separator
        try:
            return _runtime_id_separator()
        except RuntimeError:
            return "-"

    @staticmethod
    def _zip_ngb(src: Path, dest: Path, arcname: str) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(dest, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(src, arcname=arcname)
        try:
            src.unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass

    def _parse_csv_metadata(self, path: Path) -> Dict[str, str]:
        """Parse Horiba header until numeric table begins; accept TAB or ';'."""

        def _looks_like_table_header(token: str) -> bool:
            stripped = token.strip().strip('"')
            if re.match(r"^[xX]\([^)]*\)$", stripped):
                return True
            return bool(
                re.match(
                    r"^[\s]*[0-9]*[.,]?[0-9]+([\sEe][+-]?[0-9]+)?\s*$",
                    stripped,
                )
            )

        text = read_text_prefix(
            path,
            bytes_limit=_MAX_PREFIX_BYTES,
            encodings=("utf-8-sig", "utf-8", "cp1252", "latin-1"),
            errors=None,
            fallback_encoding="latin-1",
            fallback_errors="ignore",
            logger=logger,
            log_label="PSA",
        )
        if not text:
            return {}
        meta: Dict[str, str] = {}
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            parts = re.split(r"\t+|;", stripped)
            if not parts:
                continue
            first = parts[0].strip().strip('"').strip("\ufeff")
            if _looks_like_table_header(first):
                break
            if len(parts) >= 2:
                key = first.lower()
                value = parts[1].strip().strip('"')
                if key and value:
                    meta[key] = value
        if meta:
            logger.debug(
                "PSA: parsed metadata keys=%s probenname=%r from %s",
                sorted(list(meta.keys()))[:10],
                meta.get(_PROBENAME_KEY),
                path,
            )
        return meta

    def _purge_stale(self) -> None:
        now = time.time()
        ttl_seconds = getattr(
            getattr(self.device_config, "batch", None), "ttl_seconds", 600
        )

        for folder_key, state in list(self._state.items()):
            moved_pending = 0
            moved_pairs = 0
            moved_sentinel = 0
            refreshed_pending: Deque[_PendingNGB] = deque()
            for pending in list(state.pending_ngb):
                if now - pending.created > ttl_seconds:
                    if pending.path.exists():
                        logger.info(
                            "PSA: moving '%s' to exception folder (stale pending NGB)",
                            pending.path,
                        )
                        try:
                            safe_move_to_exception(str(pending.path))
                        except Exception:  # noqa: BLE001
                            logger.exception(
                                "PSA: failed to move %s to exception", pending.path
                            )
                    moved_pending += 1
                else:
                    refreshed_pending.append(pending)
            state.pending_ngb = refreshed_pending

            refreshed_pairs: List[_Pair] = []
            for pair in list(state.bucket):
                if now - pair.created > ttl_seconds:
                    for path, reason in (
                        (pair.csv_path, "stale queued CSV"),
                        (pair.ngb_path, "stale queued NGB"),
                    ):
                        if path.exists():
                            logger.info(
                                "PSA: moving '%s' to exception folder (%s)",
                                path,
                                reason,
                            )
                            try:
                                safe_move_to_exception(str(path))
                            except Exception:  # noqa: BLE001
                                logger.exception(
                                    "PSA: failed to move %s to exception", path
                                )
                    moved_pairs += 1
                else:
                    refreshed_pairs.append(pair)
            state.bucket = refreshed_pairs

            sentinel = state.sentinel
            if sentinel and now - sentinel.created > ttl_seconds:
                if sentinel.csv_path.exists():
                    logger.info(
                        "PSA: moving '%s' to exception folder (stale sentinel CSV)",
                        sentinel.csv_path,
                    )
                    try:
                        safe_move_to_exception(str(sentinel.csv_path))
                    except Exception:  # noqa: BLE001
                        logger.exception(
                            "PSA: failed to move %s to exception", sentinel.csv_path
                        )
                state.sentinel = None
                moved_sentinel += 1

            self._cleanup_state(folder_key)
            if moved_pending or moved_pairs or moved_sentinel:
                logger.info(
                    "PSA: purged stale in %s -> pending=%d pairs=%d sentinel=%d",
                    folder_key,
                    moved_pending,
                    moved_pairs,
                    moved_sentinel,
                )

        for folder_key in list(self._state.keys()):
            parent = Path(folder_key)
            try:
                stale_dirs = find_stale_stage_dirs(
                    parent,
                    marker=".__staged__",
                    ttl_seconds=ttl_seconds,
                    now=now,
                    active=self._finalizing.keys(),
                )
                for child in stale_dirs:
                    logger.info(
                        "PSA: moving stale staging folder '%s' to exception", child
                    )
                    try:
                        safe_move_to_exception(str(child))
                    except Exception:  # noqa: BLE001
                        logger.exception(
                            "PSA: failed to move stale staging folder %s to exception",
                            child,
                        )
            except Exception:  # noqa: BLE001
                continue

    def _create_unique_stage_dir(self, base_dir: Path, prefix: str) -> Path:
        return create_unique_stage_dir(
            base_dir, prefix, marker=".__staged__", max_index=1000
        )

    def _reconstruct_batch_from_stage(self, stage_dir: Path) -> _FlushBatch:
        prefix, pairs = reconstruct_pairs_from_stage(
            stage_dir,
            _is_csv_like,
            _is_ngb,
            marker=".__staged__",
            left_label="CSV",
            right_label="NGB",
        )
        staged_pairs: List[_Pair] = []
        for csv_path, ngb_path in pairs:
            staged_pairs.append(
                _Pair(csv_path=csv_path, ngb_path=ngb_path, created=time.time())
            )
        return _FlushBatch(prefix=prefix, raw_probenname=prefix, pairs=staged_pairs)
