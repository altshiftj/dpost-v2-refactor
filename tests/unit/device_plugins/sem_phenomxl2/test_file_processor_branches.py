"""Branch-focused tests for SEM Phenom XL2 processor helper paths."""

from __future__ import annotations

from pathlib import Path

import pytest

from dpost.device_plugins.sem_phenomxl2.file_processor import FileProcessorSEMPhenomXL2
from dpost.device_plugins.sem_phenomxl2.settings import build_config


@pytest.fixture
def processor() -> FileProcessorSEMPhenomXL2:
    """Return SEM processor configured for branch tests."""
    return FileProcessorSEMPhenomXL2(build_config())


def test_zip_export_returns_placeholder_when_export_folder_missing(
    tmp_path: Path,
    processor: FileProcessorSEMPhenomXL2,
) -> None:
    """Return expected zip path when ELID folder has no export subfolder."""
    elid_dir = tmp_path / "elid"
    elid_dir.mkdir()
    record_dir = tmp_path / "record"
    record_dir.mkdir()

    result = processor._zip_export(elid_dir, record_dir, "prefix")

    assert result == record_dir / "prefix.zip"


def test_move_descriptors_handles_skip_unique_and_move_error(
    tmp_path: Path,
    processor: FileProcessorSEMPhenomXL2,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Skip disallowed files, choose unique names for collisions, and log move failures."""
    elid_dir = tmp_path / "elid"
    elid_dir.mkdir()
    record_dir = tmp_path / "record"
    record_dir.mkdir()
    descriptor_elid = elid_dir / "sample.elid"
    descriptor_elid.write_text("meta")
    descriptor_odt = elid_dir / "sample.odt"
    descriptor_odt.write_text("doc")
    descriptor_skip = elid_dir / "sample.bin"
    descriptor_skip.write_text("bin")
    existing_dest = record_dir / "prefix.elid"
    existing_dest.write_text("existing")
    unique_dest = record_dir / "prefix-02.elid"
    moves: list[tuple[str, str]] = []

    def fake_move(src: str, dest: str) -> None:
        moves.append((src, dest))
        if src.endswith(".odt"):
            raise RuntimeError("move failed")

    monkeypatch.setattr(
        "dpost.device_plugins.sem_phenomxl2.file_processor.get_unique_filename",
        lambda _record_dir, _base, _extension, **_kwargs: str(unique_dest),
    )
    monkeypatch.setattr(
        "dpost.device_plugins.sem_phenomxl2.file_processor.move_item",
        fake_move,
    )

    processor._move_descriptors(elid_dir, record_dir, "prefix")

    assert (str(descriptor_elid), str(unique_dest)) in moves
    assert any(src.endswith(".odt") for src, _ in moves)
    assert all(not src.endswith(".bin") for src, _ in moves)


def test_cleanup_logs_error_when_rmtree_fails(
    tmp_path: Path,
    processor: FileProcessorSEMPhenomXL2,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Suppress cleanup exceptions to keep processing flow resilient."""
    elid_dir = tmp_path / "elid"
    elid_dir.mkdir()
    monkeypatch.setattr(
        "dpost.device_plugins.sem_phenomxl2.file_processor.shutil.rmtree",
        lambda _path: (_ for _ in ()).throw(OSError("cleanup failed")),
    )

    processor._cleanup(elid_dir)
