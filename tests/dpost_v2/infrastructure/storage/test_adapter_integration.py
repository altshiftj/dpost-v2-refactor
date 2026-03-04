from __future__ import annotations

from datetime import date
from pathlib import Path

from dpost_v2.infrastructure.storage.file_ops import LocalFileOpsAdapter
from dpost_v2.infrastructure.storage.staging_dirs import derive_staging_layout


def test_file_ops_moves_artifact_between_derived_staging_buckets(tmp_path: Path) -> None:
    layout = derive_staging_layout(
        root=tmp_path / "root",
        profile="qa",
        mode="headless",
        processing_date=date(2026, 3, 4),
        device_token="xrd",
        create_on_demand=True,
    )
    source = layout.staging / "artifact.txt"
    source.write_text("payload", encoding="utf-8")
    target = layout.processed / "artifact.txt"

    adapter = LocalFileOpsAdapter(layout.root)
    moved = adapter.move(str(source), str(target))

    assert Path(moved) == target
    assert source.exists() is False
    assert target.read_text(encoding="utf-8") == "payload"
