from __future__ import annotations

from pathlib import PurePath

import pytest

from dpost_v2.plugins.devices.psa_horiba.plugin import create_processor
from tests.dpost_v2.plugins.devices._helpers import processing_context_for


def test_psa001_can_process_tsv_exports_in_addition_to_csv_and_ngb() -> None:
    processor = create_processor({})

    assert processor.can_process({"source_path": "D:/incoming/export.tsv"}) is True


def test_psa002_process_sentinel_sequence_emits_numbered_csv_and_zip_artifacts(
    tmp_path,
) -> None:
    processor = create_processor({})
    ngb_first = tmp_path / "s01.ngb"
    csv_first = tmp_path / "s01.csv"
    csv_sentinel = tmp_path / "sentinel.csv"
    ngb_sentinel = tmp_path / "sentinel.ngb"
    ngb_first.write_bytes(b"ngb-first")
    csv_first.write_text(
        "Probenname\tBucket Sample\nX(mm)\tValue\n",
        encoding="utf-8",
    )
    csv_sentinel.write_text(
        "Probenname;Final Sample\nX(mm);Value\n",
        encoding="utf-8",
    )
    ngb_sentinel.write_bytes(b"ngb-second")

    processor.prepare({"source_path": str(ngb_first)})
    processor.prepare({"source_path": str(csv_first)})
    processor.prepare({"source_path": str(csv_sentinel)})
    prepared = processor.prepare({"source_path": str(ngb_sentinel)})
    result = processor.process(prepared, processing_context_for(str(ngb_sentinel)))

    artifact_names = {
        PurePath(path).name for path in (result.final_path, *result.force_paths)
    }
    assert result.datatype == "psa"
    assert artifact_names == {
        "Final Sample-01.csv",
        "Final Sample-01.zip",
        "Final Sample-02.csv",
        "Final Sample-02.zip",
    }


def test_psa003_process_requires_complete_sentinel_sequence_before_finalize(
    tmp_path,
) -> None:
    processor = create_processor({})
    csv_sentinel = tmp_path / "sentinel.csv"
    csv_sentinel.write_text(
        "Probenname;Final Sample\nX(mm);Value\n",
        encoding="utf-8",
    )

    prepared = processor.prepare({"source_path": str(csv_sentinel)})

    with pytest.raises((KeyError, ValueError), match="sentinel|batch|pair|stage"):
        processor.process(prepared, processing_context_for(str(csv_sentinel)))
