from __future__ import annotations

import pytest

from dpost_v2.plugins.devices.utm_zwick.plugin import create_processor
from tests.dpost_v2.plugins.devices._helpers import processing_context_for


def test_utm001_process_matching_xlsx_trigger_emits_raw_and_results_artifacts(
    tmp_path,
) -> None:
    processor = create_processor({})
    zs2_path = tmp_path / "usr-inst-sample_a.zs2"
    xlsx_path = tmp_path / "usr-inst-sample_a.xlsx"
    zs2_path.write_bytes(b"raw")
    xlsx_path.write_bytes(b"results")

    processor.prepare({"source_path": str(zs2_path)})
    prepared = processor.prepare({"source_path": str(xlsx_path)})
    result = processor.process(prepared, processing_context_for(str(xlsx_path)))

    assert result.datatype == "xlsx"
    assert result.final_path == str(xlsx_path)
    assert result.force_paths == (str(zs2_path), str(xlsx_path))


def test_utm002_process_rejects_orphan_xlsx_without_matching_zs2(tmp_path) -> None:
    processor = create_processor({})
    xlsx_path = tmp_path / "usr-inst-sample_a.xlsx"
    xlsx_path.write_bytes(b"results")

    prepared = processor.prepare({"source_path": str(xlsx_path)})

    with pytest.raises((KeyError, ValueError), match="zs2|series|staged|pair"):
        processor.process(prepared, processing_context_for(str(xlsx_path)))


def test_utm003_process_requires_exact_stem_match_for_series_pairing(tmp_path) -> None:
    processor = create_processor({})
    zs2_path = tmp_path / "Usr-Inst-SampleA.zs2"
    xlsx_path = tmp_path / "usr-inst-samplea.xlsx"
    zs2_path.write_bytes(b"raw")
    xlsx_path.write_bytes(b"results")

    processor.prepare({"source_path": str(zs2_path)})
    prepared = processor.prepare({"source_path": str(xlsx_path)})

    with pytest.raises((KeyError, ValueError), match="zs2|series|staged|pair"):
        processor.process(prepared, processing_context_for(str(xlsx_path)))


def test_utm004_prepare_stages_zs2_without_becoming_processable(tmp_path) -> None:
    processor = create_processor({})
    zs2_path = tmp_path / "usr-inst-sample_a.zs2"
    zs2_path.write_bytes(b"raw")

    prepared = processor.prepare({"source_path": str(zs2_path)})

    assert prepared["extension"] == ".zs2"
    assert processor.can_process(prepared) is False


def test_utm005_can_process_only_xlsx_with_matching_staged_zs2(tmp_path) -> None:
    processor = create_processor({})
    zs2_path = tmp_path / "usr-inst-sample_a.zs2"
    xlsx_path = tmp_path / "usr-inst-sample_a.xlsx"
    zs2_path.write_bytes(b"raw")
    xlsx_path.write_bytes(b"results")

    orphan = processor.prepare({"source_path": str(xlsx_path)})
    assert processor.can_process(orphan) is False

    processor.prepare({"source_path": str(zs2_path)})
    prepared = processor.prepare({"source_path": str(xlsx_path)})

    assert processor.can_process(prepared) is True
