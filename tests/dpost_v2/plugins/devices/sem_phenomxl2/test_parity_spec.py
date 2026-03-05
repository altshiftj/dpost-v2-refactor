from __future__ import annotations

from pathlib import PurePath

from dpost_v2.plugins.devices.sem_phenomxl2.plugin import create_processor
from tests.dpost_v2.plugins.devices._helpers import processing_context_for


def test_sem001_can_process_elid_directories() -> None:
    processor = create_processor({})

    assert processor.can_process({"source_path": "D:/incoming/analysis.elid"}) is True


def test_sem002_process_native_image_normalizes_trailing_digit_and_sets_img_datatype() -> (
    None
):
    processor = create_processor({})
    source_path = "D:/incoming/image3.tif"

    prepared = processor.prepare({"source_path": source_path})
    result = processor.process(prepared, processing_context_for(source_path))

    assert result.datatype == "img"
    assert PurePath(result.final_path).name == "image.tif"


def test_sem003_process_elid_directory_emits_zip_and_descriptor_artifacts(
    tmp_path,
) -> None:
    processor = create_processor({})
    elid_dir = tmp_path / "analysis.elid"
    export_dir = elid_dir / "export"
    export_dir.mkdir(parents=True)
    (export_dir / "payload.bin").write_bytes(b"42")
    (elid_dir / "analysis.odt").write_text("note", encoding="utf-8")
    (elid_dir / "analysis.elid").write_text("meta", encoding="utf-8")

    prepared = processor.prepare({"source_path": str(elid_dir)})
    result = processor.process(prepared, processing_context_for(str(elid_dir)))

    artifact_names = {
        PurePath(path).name for path in (result.final_path, *result.force_paths)
    }
    assert result.datatype == "elid"
    assert "analysis.zip" in artifact_names
    assert "analysis.odt" in artifact_names
    assert "analysis.elid" in artifact_names
