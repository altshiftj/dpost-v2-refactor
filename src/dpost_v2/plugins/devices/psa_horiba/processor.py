"""Contract-local PSA Horiba processor preserving sentinel batch semantics."""

from __future__ import annotations

import re
import shutil
import time
import zipfile
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from dpost_v2.application.contracts.context import ProcessingContext
from dpost_v2.application.contracts.plugin_contracts import ProcessorResult
from dpost_v2.plugins.devices._device_template.processor import (
    DeviceProcessorFormatError,
    DeviceProcessorValidationError,
)
from dpost_v2.plugins.devices.psa_horiba.settings import DevicePluginSettings

_DEFAULT_STALE_AFTER_SECONDS = 600.0
_PROBENAME_KEY = "probenname"
_STAGE_MARKER = ".__staged__"
_STAGE_READY_KIND = "staged_batch"
_WAITING_KINDS = frozenset(
    {
        "awaiting_export_pair",
        "awaiting_sentinel_pair",
        "bucketed_pair",
    }
)


@dataclass(slots=True)
class _PendingNgb:
    path: Path
    created_at: float


@dataclass(slots=True)
class _Pair:
    csv_path: Path
    ngb_path: Path
    created_at: float


@dataclass(slots=True)
class _Sentinel:
    csv_path: Path
    prefix: str
    created_at: float


@dataclass(slots=True)
class _FolderState:
    pending_ngb: deque[_PendingNgb] = field(default_factory=deque)
    bucket: list[_Pair] = field(default_factory=list)
    sentinel: _Sentinel | None = None

    def is_idle(self) -> bool:
        return not self.pending_ngb and not self.bucket and self.sentinel is None


@dataclass(slots=True)
class _StagedBatch:
    stage_dir: Path
    prefix: str
    pairs: tuple[_Pair, ...]
    created_at: float


@dataclass(slots=True)
class DeviceProcessor:
    """PSA processor with contract-local deferred staging semantics."""

    settings: DevicePluginSettings
    _state: dict[str, _FolderState] = field(
        default_factory=dict, init=False, repr=False
    )
    _staged_batches: dict[str, _StagedBatch] = field(
        default_factory=dict,
        init=False,
        repr=False,
    )
    _ngb_to_stage: dict[str, str] = field(default_factory=dict, init=False, repr=False)

    def prepare(self, raw_input: Mapping[str, Any]) -> Mapping[str, Any]:
        """Stage PSA files until a complete sentinel batch is ready to finalize."""
        if not isinstance(raw_input, Mapping):
            raise DeviceProcessorFormatError("raw_input must be a mapping")

        source_path = self._require_source_path(raw_input)
        staged_path = self._ngb_to_stage.get(source_path)
        if staged_path is not None:
            return self._build_staged_payload(Path(staged_path))

        extension = self._normalize_extension(source_path)
        if extension not in self.settings.source_extensions:
            raise DeviceProcessorFormatError(
                f"unsupported extension {extension!r} for {self.settings.plugin_id}"
            )

        path = Path(source_path)
        if not path.exists():
            raise DeviceProcessorValidationError("source_path does not exist")

        now = time.time()
        self._purge_stale(now)

        folder_key = str(path.parent.resolve())
        state = self._state.setdefault(folder_key, _FolderState())

        if extension in {".csv", ".tsv"}:
            return self._prepare_csv(path=path, state=state, now=now)
        if extension == ".ngb":
            return self._prepare_ngb(
                path=path,
                folder_key=folder_key,
                state=state,
                now=now,
            )
        raise DeviceProcessorFormatError(
            f"unsupported extension {extension!r} for {self.settings.plugin_id}"
        )

    def can_process(self, candidate: Mapping[str, Any]) -> bool:
        """Only finalize ready staged batches; raw TSV probing remains supported."""
        prepared_kind = str(candidate.get("prepared_kind", "")).strip()
        if prepared_kind in _WAITING_KINDS:
            return False
        if prepared_kind == _STAGE_READY_KIND:
            return True

        source_path = str(candidate.get("source_path", "")).strip()
        if "." not in source_path:
            return False
        return self._normalize_extension(source_path) in self.settings.source_extensions

    def process(
        self,
        prepared_input: Mapping[str, Any],
        context: ProcessingContext,
    ) -> ProcessorResult:
        """Finalize a staged PSA batch or fail clearly for incomplete sentinel state."""
        _ = context
        prepared_kind = str(prepared_input.get("prepared_kind", "")).strip()
        if prepared_kind in _WAITING_KINDS:
            raise ValueError("sentinel batch pair is incomplete and cannot finalize")
        if prepared_kind == _STAGE_READY_KIND:
            return self._process_staged_batch(prepared_input)

        source_path = self._require_source_path(prepared_input)
        return ProcessorResult(
            final_path=source_path,
            datatype="psa_horiba/template",
        )

    def _prepare_csv(
        self,
        *,
        path: Path,
        state: _FolderState,
        now: float,
    ) -> Mapping[str, Any]:
        prefix = self._parse_csv_prefix(path)
        if state.pending_ngb:
            pending = state.pending_ngb.popleft()
            state.bucket.append(
                _Pair(
                    csv_path=path,
                    ngb_path=pending.path,
                    created_at=now,
                )
            )
            return self._build_waiting_payload(path, "bucketed_pair", prefix=prefix)

        state.sentinel = _Sentinel(
            csv_path=path,
            prefix=prefix,
            created_at=now,
        )
        return self._build_waiting_payload(
            path, "awaiting_sentinel_pair", prefix=prefix
        )

    def _prepare_ngb(
        self,
        *,
        path: Path,
        folder_key: str,
        state: _FolderState,
        now: float,
    ) -> Mapping[str, Any]:
        sentinel = state.sentinel
        if sentinel is None:
            state.pending_ngb.append(_PendingNgb(path=path, created_at=now))
            return self._build_waiting_payload(path, "awaiting_export_pair")

        stage_prefix = sentinel.prefix or sentinel.csv_path.stem or "psa"
        stage_dir = self._create_unique_stage_dir(path.parent, stage_prefix)
        staged_pairs = [
            *state.bucket,
            _Pair(csv_path=sentinel.csv_path, ngb_path=path, created_at=now),
        ]
        relocated_pairs = tuple(
            self._relocate_pair_to_stage(pair=pair, stage_dir=stage_dir)
            for pair in staged_pairs
        )
        self._staged_batches[str(stage_dir)] = _StagedBatch(
            stage_dir=stage_dir,
            prefix=stage_prefix,
            pairs=relocated_pairs,
            created_at=now,
        )
        self._ngb_to_stage[str(path)] = str(stage_dir)

        state.pending_ngb.clear()
        state.bucket.clear()
        state.sentinel = None
        self._cleanup_state(folder_key)

        return self._build_staged_payload(stage_dir)

    def _process_staged_batch(
        self,
        prepared_input: Mapping[str, Any],
    ) -> ProcessorResult:
        stage_dir = Path(self._require_source_path(prepared_input))
        output_dir = Path(
            str(prepared_input.get("output_dir", "")).strip() or str(stage_dir.parent)
        )
        batch = self._staged_batches.pop(str(stage_dir), None)
        if batch is None:
            batch = self._reconstruct_batch_from_stage(stage_dir)
        if not batch.pairs:
            raise ValueError("stage batch has no pairs to finalize")

        output_dir.mkdir(parents=True, exist_ok=True)
        created_paths: list[str] = []
        for pair in batch.pairs:
            if not pair.csv_path.exists() or not pair.ngb_path.exists():
                raise ValueError("stage batch pair is incomplete")

            basename = self._next_sequence_basename(output_dir, batch.prefix)
            csv_dest = output_dir / f"{basename}.csv"
            zip_dest = output_dir / f"{basename}.zip"

            shutil.move(str(pair.csv_path), str(csv_dest))
            self._zip_ngb(pair.ngb_path, zip_dest, f"{basename}.ngb")
            created_paths.extend((str(csv_dest), str(zip_dest)))

        self._cleanup_stage_dir(stage_dir)
        self._remove_stage_reverse_mappings(stage_dir)

        return ProcessorResult(
            final_path=created_paths[0],
            datatype="psa",
            force_paths=tuple(created_paths[1:]),
        )

    def _purge_stale(self, now: float) -> None:
        ttl_seconds = self._stale_after_seconds()
        for folder_key, state in list(self._state.items()):
            state.pending_ngb = deque(
                pending
                for pending in state.pending_ngb
                if now - pending.created_at <= ttl_seconds and pending.path.exists()
            )
            state.bucket = [
                pair
                for pair in state.bucket
                if (
                    now - pair.created_at <= ttl_seconds
                    and pair.csv_path.exists()
                    and pair.ngb_path.exists()
                )
            ]
            if state.sentinel is not None:
                sentinel = state.sentinel
                if (
                    now - sentinel.created_at > ttl_seconds
                    or not sentinel.csv_path.exists()
                ):
                    state.sentinel = None
            self._cleanup_state(folder_key)

        stale_stage_dirs = [
            batch.stage_dir
            for batch in self._staged_batches.values()
            if now - batch.created_at > ttl_seconds or not batch.stage_dir.exists()
        ]
        for stage_dir in stale_stage_dirs:
            self._staged_batches.pop(str(stage_dir), None)
            self._remove_stage_reverse_mappings(stage_dir)

    def _parse_csv_prefix(self, path: Path) -> str:
        metadata = self._parse_csv_metadata(path)
        return metadata.get(_PROBENAME_KEY, "").strip()

    def _parse_csv_metadata(self, path: Path) -> dict[str, str]:
        text = self._read_text_prefix(path)
        metadata: dict[str, str] = {}
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            parts = re.split(r"\t+|;", stripped)
            if not parts:
                continue
            key = parts[0].strip().strip('"').strip("\ufeff")
            if self._looks_like_table_header(key):
                break
            if len(parts) >= 2:
                value = parts[1].strip().strip('"')
                if key and value:
                    metadata[key.lower()] = value
        return metadata

    @staticmethod
    def _looks_like_table_header(token: str) -> bool:
        if re.match(r"^[xX]\([^)]*\)$", token):
            return True
        return bool(
            re.match(
                r"^[\s]*[0-9]*[.,]?[0-9]+([\sEe][+-]?[0-9]+)?\s*$",
                token,
            )
        )

    @staticmethod
    def _read_text_prefix(path: Path) -> str:
        raw_bytes = path.read_bytes()[:200_000]
        for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
            try:
                return raw_bytes.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw_bytes.decode("latin-1", errors="ignore")

    def _create_unique_stage_dir(self, base_dir: Path, prefix: str) -> Path:
        safe_prefix = prefix or "psa"
        index = 1
        while True:
            candidate = base_dir / f"{safe_prefix}{_STAGE_MARKER}{index:02d}"
            if not candidate.exists():
                candidate.mkdir(parents=True, exist_ok=False)
                return candidate
            index += 1

    @staticmethod
    def _relocate_pair_to_stage(*, pair: _Pair, stage_dir: Path) -> _Pair:
        staged_csv = stage_dir / pair.csv_path.name
        staged_ngb = stage_dir / pair.ngb_path.name
        shutil.move(str(pair.csv_path), str(staged_csv))
        shutil.move(str(pair.ngb_path), str(staged_ngb))
        return _Pair(
            csv_path=staged_csv,
            ngb_path=staged_ngb,
            created_at=pair.created_at,
        )

    def _reconstruct_batch_from_stage(self, stage_dir: Path) -> _StagedBatch:
        if not stage_dir.is_dir():
            raise ValueError("stage directory is missing for PSA batch reconstruction")

        csv_paths = sorted(
            path
            for path in stage_dir.iterdir()
            if path.is_file() and path.suffix.lower() in {".csv", ".tsv"}
        )
        ngb_paths = sorted(
            path
            for path in stage_dir.iterdir()
            if path.is_file() and path.suffix.lower() == ".ngb"
        )
        if len(csv_paths) != len(ngb_paths) or not csv_paths:
            raise ValueError("stage pair reconstruction failed for PSA batch")

        csv_by_stem = self._group_by_stem(csv_paths)
        ngb_by_stem = self._group_by_stem(ngb_paths)

        paired_paths: list[tuple[Path, Path]] = []
        for stem in sorted(set(csv_by_stem) & set(ngb_by_stem)):
            csv_group = csv_by_stem[stem]
            ngb_group = ngb_by_stem[stem]
            while csv_group and ngb_group:
                paired_paths.append((csv_group.pop(0), ngb_group.pop(0)))

        remaining_csv = sorted(path for paths in csv_by_stem.values() for path in paths)
        remaining_ngb = sorted(path for paths in ngb_by_stem.values() for path in paths)
        if len(remaining_csv) != len(remaining_ngb):
            raise ValueError("stage pair reconstruction failed for PSA batch")

        paired_paths.extend(zip(remaining_csv, remaining_ngb, strict=True))
        prefix = stage_dir.name.split(_STAGE_MARKER, maxsplit=1)[0] or "psa"
        created_at = time.time()
        return _StagedBatch(
            stage_dir=stage_dir,
            prefix=prefix,
            pairs=tuple(
                _Pair(csv_path=csv_path, ngb_path=ngb_path, created_at=created_at)
                for csv_path, ngb_path in paired_paths
            ),
            created_at=created_at,
        )

    @staticmethod
    def _group_by_stem(paths: list[Path]) -> dict[str, list[Path]]:
        grouped: dict[str, list[Path]] = defaultdict(list)
        for path in paths:
            grouped[path.stem].append(path)
        return grouped

    @staticmethod
    def _zip_ngb(source_path: Path, destination_path: Path, archive_name: str) -> None:
        with zipfile.ZipFile(
            destination_path,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            archive.write(source_path, arcname=archive_name)
        source_path.unlink(missing_ok=True)

    @staticmethod
    def _cleanup_stage_dir(stage_dir: Path) -> None:
        if not stage_dir.exists():
            return
        if any(stage_dir.iterdir()):
            return
        stage_dir.rmdir()

    def _next_sequence_basename(self, directory: Path, prefix: str) -> str:
        max_index = 0
        for existing in directory.iterdir():
            if not existing.is_file():
                continue
            stem = existing.stem
            base, separator, suffix = stem.rpartition("-")
            if not separator or base != prefix:
                continue
            if suffix.isdigit():
                max_index = max(max_index, int(suffix))
        return f"{prefix}-{max_index + 1:02d}"

    def _build_waiting_payload(
        self,
        path: Path,
        prepared_kind: str,
        *,
        prefix: str | None = None,
    ) -> Mapping[str, Any]:
        payload: dict[str, Any] = {
            "source_path": str(path),
            "plugin_id": self.settings.plugin_id,
            "prepared_kind": prepared_kind,
        }
        if prefix:
            payload["prefix_hint"] = prefix
        return payload

    def _build_staged_payload(self, stage_dir: Path) -> Mapping[str, Any]:
        return {
            "source_path": str(stage_dir),
            "plugin_id": self.settings.plugin_id,
            "prepared_kind": _STAGE_READY_KIND,
            "output_dir": str(stage_dir.parent),
        }

    @staticmethod
    def _require_source_path(payload: Mapping[str, Any]) -> str:
        source_path = payload.get("source_path")
        if not isinstance(source_path, str) or not source_path.strip():
            raise DeviceProcessorValidationError("source_path is required")
        return source_path.strip()

    @staticmethod
    def _normalize_extension(source_path: str) -> str:
        if "." not in source_path:
            return ""
        return f".{source_path.rsplit('.', maxsplit=1)[-1].lower()}"

    def _stale_after_seconds(self) -> float:
        raw_value = self.settings.extra.get(
            "stale_after_seconds",
            _DEFAULT_STALE_AFTER_SECONDS,
        )
        try:
            return max(float(raw_value), 0.0)
        except (TypeError, ValueError):
            return _DEFAULT_STALE_AFTER_SECONDS

    def _remove_stage_reverse_mappings(self, stage_dir: Path) -> None:
        for source_path, mapped_stage in list(self._ngb_to_stage.items()):
            if mapped_stage == str(stage_dir):
                self._ngb_to_stage.pop(source_path, None)

    def _cleanup_state(self, folder_key: str) -> None:
        state = self._state.get(folder_key)
        if state is not None and state.is_idle():
            self._state.pop(folder_key, None)
