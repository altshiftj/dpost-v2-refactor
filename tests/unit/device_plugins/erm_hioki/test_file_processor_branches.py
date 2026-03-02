"""Branch-focused tests for ERM Hioki processor helper paths."""

from __future__ import annotations

import shutil
from pathlib import Path

from dpost.device_plugins.erm_hioki.file_processor import FileProcessorHioki
from dpost.device_plugins.erm_hioki.settings import build_config
from dpost.domain.records.local_record import LocalRecord


def test_preprocessing_probe_and_identity_branches(tmp_path: Path) -> None:
    """Cover non-CSV preprocessing plus probe/identity helper branches."""
    processor = FileProcessorHioki(build_config())
    export = tmp_path / "report.xlsx"
    export.write_text("xlsx")
    text = tmp_path / "report.txt"
    text.write_text("txt")

    passthrough = processor.device_specific_preprocessing(str(text))
    assert passthrough is not None
    assert passthrough.prefix_override is None

    assert processor.probe_file(str(export)).is_match() is True
    assert processor.probe_file(str(text)).is_mismatch() is True
    assert processor.get_device_id() == "hioki_blb"
    assert (
        processor.is_appendable(
            LocalRecord(identifier="dev-user-ipat-sample", id_separator="-"),
            "p",
            ".csv",
        )
        is True
    )


def test_processing_routes_excel_and_generic_extensions(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Route Excel and non-CSV extensions through dedicated processing helpers."""
    processor = FileProcessorHioki(build_config(), id_separator="-")
    record_dir = tmp_path / "record"
    record_dir.mkdir()
    xlsx_src = tmp_path / "sample.xlsx"
    xlsx_src.write_text("xlsx")
    dat_src = tmp_path / "sample.dat"
    dat_src.write_text("dat")
    moves: list[tuple[str, str]] = []

    monkeypatch.setattr(
        "dpost.device_plugins.erm_hioki.file_processor.get_unique_filename",
        lambda _record_path, file_id, extension, **_kwargs: str(
            record_dir / f"{file_id}{extension}"
        ),
    )
    monkeypatch.setattr(
        "dpost.device_plugins.erm_hioki.file_processor.move_item",
        lambda src, dest: moves.append((str(src), str(dest))),
    )

    excel_output = processor.device_specific_processing(
        str(xlsx_src),
        str(record_dir),
        "prefix_excel",
        ".xlsx",
    )
    generic_output = processor.device_specific_processing(
        str(dat_src),
        str(record_dir),
        "prefix_generic",
        ".dat",
    )

    assert excel_output.final_path.endswith("prefix_excel.xlsx")
    assert generic_output.final_path.endswith("prefix_generic.dat")
    assert len(moves) == 2


def test_copy_overwrite_handles_same_file_error(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Suppress SameFileError from copy operation for idempotent overwrite calls."""
    src = tmp_path / "sample.csv"
    src.write_text("csv")
    dest = tmp_path / "sample-copy.csv"
    monkeypatch.setattr(
        "dpost.device_plugins.erm_hioki.file_processor.shutil.copy2",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            shutil.SameFileError("src", "dst")
        ),
    )

    FileProcessorHioki._copy_overwrite(src, dest)
