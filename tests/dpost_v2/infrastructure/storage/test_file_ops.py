from __future__ import annotations

import errno
import shutil
from pathlib import Path

import pytest

from dpost_v2.infrastructure.storage.file_ops import (
    FileOpsCrossDeviceError,
    FileOpsNotFoundError,
    FileOpsPathSafetyError,
    LocalFileOpsAdapter,
)


def test_read_bytes_returns_file_content_within_root(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    source = root / "artifact.bin"
    source.write_bytes(b"abc123")

    adapter = LocalFileOpsAdapter(root)

    assert adapter.read_bytes(str(source)) == b"abc123"


def test_read_bytes_maps_missing_file_to_typed_error(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    adapter = LocalFileOpsAdapter(root)

    with pytest.raises(FileOpsNotFoundError):
        adapter.read_bytes(str(root / "missing.bin"))


def test_path_safety_guard_blocks_operations_outside_root(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"x")
    adapter = LocalFileOpsAdapter(root)

    with pytest.raises(FileOpsPathSafetyError):
        adapter.read_bytes(str(outside))


def test_move_falls_back_to_shutil_for_cross_device_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    source = root / "source.txt"
    source.write_text("payload", encoding="utf-8")
    target = root / "target.txt"

    adapter = LocalFileOpsAdapter(root)

    original_rename = Path.rename

    def _rename(path: Path, destination: Path) -> Path:
        raise OSError(errno.EXDEV, "cross-device")

    def _move(src: str, dst: str) -> str:
        return str(original_rename(Path(src), Path(dst)))

    monkeypatch.setattr(Path, "rename", _rename)
    monkeypatch.setattr(shutil, "move", _move)

    moved = adapter.move(str(source), str(target))

    assert Path(moved) == target
    assert target.read_text(encoding="utf-8") == "payload"


def test_move_raises_cross_device_error_when_fallback_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    source = root / "source.txt"
    source.write_text("payload", encoding="utf-8")
    target = root / "target.txt"

    adapter = LocalFileOpsAdapter(root)

    def _rename(path: Path, destination: Path) -> Path:
        raise OSError(errno.EXDEV, "cross-device")

    def _move(src: str, dst: str) -> str:
        raise OSError(errno.EXDEV, "move failed")

    monkeypatch.setattr(Path, "rename", _rename)
    monkeypatch.setattr(shutil, "move", _move)

    with pytest.raises(FileOpsCrossDeviceError):
        adapter.move(str(source), str(target))


def test_delete_missing_path_is_idempotent_safe_noop(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    adapter = LocalFileOpsAdapter(root, safe_noop=True)

    adapter.delete(str(root / "never-created.txt"))


def test_mkdir_and_exists_are_scoped_to_root(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    nested = root / "a" / "b"
    adapter = LocalFileOpsAdapter(root)

    adapter.mkdir(str(nested))

    assert adapter.exists(str(nested)) is True
