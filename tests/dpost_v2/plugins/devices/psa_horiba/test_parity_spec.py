from __future__ import annotations

from pathlib import PurePath

import pytest

from dpost_v2.plugins.devices.psa_horiba.plugin import create_processor
from dpost_v2.plugins.devices.psa_horiba import processor as psa_processor_module
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
    replayed = processor.prepare({"source_path": str(ngb_sentinel)})

    assert PurePath(str(prepared["source_path"])).name == "Final Sample.__staged__01"
    assert replayed["source_path"] == prepared["source_path"]

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


def test_psa004_prepare_purges_stale_pending_ngb_before_pairing(
    tmp_path,
    monkeypatch,
) -> None:
    tick = {"now": 1_000.0}
    monkeypatch.setattr(psa_processor_module.time, "time", lambda: tick["now"])

    processor = create_processor({"stale_after_seconds": 30})
    stale_ngb = tmp_path / "stale.ngb"
    fresh_csv = tmp_path / "fresh.csv"
    fresh_ngb = tmp_path / "fresh.ngb"
    stale_ngb.write_bytes(b"stale")
    fresh_csv.write_text(
        "Probenname;Fresh Sample\nX(mm);Value\n",
        encoding="utf-8",
    )
    fresh_ngb.write_bytes(b"fresh")

    processor.prepare({"source_path": str(stale_ngb)})
    tick["now"] = 1_035.0
    processor.prepare({"source_path": str(fresh_csv)})
    tick["now"] = 1_036.0
    prepared = processor.prepare({"source_path": str(fresh_ngb)})
    result = processor.process(prepared, processing_context_for(str(fresh_ngb)))

    artifact_names = {
        PurePath(path).name for path in (result.final_path, *result.force_paths)
    }
    assert artifact_names == {"Fresh Sample-01.csv", "Fresh Sample-01.zip"}
