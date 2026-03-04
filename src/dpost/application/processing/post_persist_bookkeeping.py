"""Planning and emission helpers for post-persist bookkeeping side effects."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from dpost.application.processing.force_path_policy import ResolvedForcePath


@dataclass(frozen=True)
class PostPersistRecordUpdateTarget:
    """One record-update target and any files to mark unsynced beneath it."""

    path: str
    unsynced_paths: tuple[str, ...] = tuple()


@dataclass(frozen=True)
class PostPersistBookkeepingPlan:
    """Computed post-persist bookkeeping work items and skipped force paths."""

    update_targets: tuple[PostPersistRecordUpdateTarget, ...]
    skipped_missing_force_paths: tuple[str, ...] = tuple()


@dataclass(frozen=True)
class PostPersistBookkeepingEmissionSink:
    """Injectable sink callables used to emit bookkeeping side effects."""

    update_record: Callable[[str], int]
    mark_file_as_unsynced: Callable[[str], None]
    increment_processed_metric: Callable[[int], None]


def build_post_persist_bookkeeping_plan(
    final_path: str,
    resolved_force_paths: Iterable[ResolvedForcePath],
    *,
    iter_force_unsynced_targets_fn: Callable[[Path], Iterable[Path]],
) -> PostPersistBookkeepingPlan:
    """Build a post-persist bookkeeping plan from resolved force paths."""
    update_targets: list[PostPersistRecordUpdateTarget] = [
        PostPersistRecordUpdateTarget(path=final_path)
    ]
    skipped_missing: list[str] = []

    for resolved in resolved_force_paths:
        if not resolved.exists:
            skipped_missing.append(resolved.raw_path)
            continue
        unsynced_paths = tuple(
            str(child)
            for child in iter_force_unsynced_targets_fn(resolved.resolved_path)
        )
        update_targets.append(
            PostPersistRecordUpdateTarget(
                path=str(resolved.resolved_path),
                unsynced_paths=unsynced_paths,
            )
        )

    return PostPersistBookkeepingPlan(
        update_targets=tuple(update_targets),
        skipped_missing_force_paths=tuple(skipped_missing),
    )


def emit_post_persist_bookkeeping(
    plan: PostPersistBookkeepingPlan,
    sink: PostPersistBookkeepingEmissionSink,
) -> int:
    """Emit record updates, unsynced markers, and processed metrics from a plan."""
    new_files = 0
    for target in plan.update_targets:
        new_files += sink.update_record(target.path)
        for unsynced_path in target.unsynced_paths:
            sink.mark_file_as_unsynced(unsynced_path)
    if new_files > 0:
        sink.increment_processed_metric(new_files)
    return new_files
