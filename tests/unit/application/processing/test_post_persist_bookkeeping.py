"""Unit tests for post-persist bookkeeping planning and emission helpers."""

from __future__ import annotations

from pathlib import Path

from dpost.application.processing.force_path_policy import ResolvedForcePath
from dpost.application.processing.force_path_policy import iter_force_unsynced_targets
from dpost.application.processing.post_persist_bookkeeping import (
    PostPersistBookkeepingEmissionSink,
    PostPersistBookkeepingPlan,
    PostPersistRecordUpdateTarget,
    build_post_persist_bookkeeping_plan,
    emit_post_persist_bookkeeping,
)


def test_build_post_persist_bookkeeping_plan_collects_targets_and_skips_missing(
    tmp_path: Path,
) -> None:
    """Build final/force update targets and track missing force-path inputs."""
    record_dir = tmp_path / "record"
    record_dir.mkdir()
    force_file = record_dir / "force.csv"
    force_file.write_text("f")
    force_dir = record_dir / "force-dir"
    nested = force_dir / "nested"
    nested.mkdir(parents=True)
    child_a = force_dir / "a.csv"
    child_b = nested / "b.csv"
    child_a.write_text("a")
    child_b.write_text("b")

    plan = build_post_persist_bookkeeping_plan(
        str(record_dir / "measurement.csv"),
        (
            ResolvedForcePath(
                raw_path="missing.csv",
                resolved_path=record_dir / "missing.csv",
                exists=False,
            ),
            ResolvedForcePath(
                raw_path="force.csv",
                resolved_path=force_file,
                exists=True,
            ),
            ResolvedForcePath(
                raw_path="force-dir",
                resolved_path=force_dir,
                exists=True,
            ),
        ),
        iter_force_unsynced_targets_fn=iter_force_unsynced_targets,
    )

    assert [target.path for target in plan.update_targets] == [
        str(record_dir / "measurement.csv"),
        str(force_file),
        str(force_dir),
    ]
    assert set(plan.update_targets[1].unsynced_paths) == {str(force_file)}
    assert set(plan.update_targets[2].unsynced_paths) == {str(child_a), str(child_b)}
    assert plan.skipped_missing_force_paths == ("missing.csv",)


def test_emit_post_persist_bookkeeping_emits_updates_unsynced_marks_and_metric() -> None:
    """Sum update counts, emit unsynced marks, and increment processed metric."""
    calls: list[tuple[str, object]] = []
    sink = PostPersistBookkeepingEmissionSink(
        update_record=lambda path: calls.append(("update", path)) or 1,
        mark_file_as_unsynced=lambda path: calls.append(("unsynced", path)),
        increment_processed_metric=lambda count: calls.append(("metric", count)),
    )
    plan = PostPersistBookkeepingPlan(
        update_targets=(
            PostPersistRecordUpdateTarget("C:/record/final.csv"),
            PostPersistRecordUpdateTarget(
                "C:/record/force-dir",
                unsynced_paths=("C:/record/force-dir/a.csv", "C:/record/force-dir/b.csv"),
            ),
        )
    )

    new_files = emit_post_persist_bookkeeping(plan, sink)

    assert new_files == 2
    assert calls == [
        ("update", "C:/record/final.csv"),
        ("update", "C:/record/force-dir"),
        ("unsynced", "C:/record/force-dir/a.csv"),
        ("unsynced", "C:/record/force-dir/b.csv"),
        ("metric", 2),
    ]


def test_emit_post_persist_bookkeeping_skips_metric_when_no_new_files() -> None:
    """Do not increment processed metric when no updates add new files."""
    calls: list[tuple[str, object]] = []
    sink = PostPersistBookkeepingEmissionSink(
        update_record=lambda path: calls.append(("update", path)) or 0,
        mark_file_as_unsynced=lambda path: calls.append(("unsynced", path)),
        increment_processed_metric=lambda count: calls.append(("metric", count)),
    )
    plan = PostPersistBookkeepingPlan(
        update_targets=(PostPersistRecordUpdateTarget("C:/record/final.csv"),)
    )

    new_files = emit_post_persist_bookkeeping(plan, sink)

    assert new_files == 0
    assert calls == [("update", "C:/record/final.csv")]

