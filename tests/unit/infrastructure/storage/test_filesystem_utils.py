from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from dpost.domain.records.local_record import LocalRecord
from dpost.infrastructure.storage import filesystem_utils


def test_init_dirs_uses_explicit_directory_list(tmp_path: Path):
    """Create explicitly provided directories without reading active config."""
    one = tmp_path / "one"
    two = tmp_path / "nested" / "two"

    filesystem_utils.init_dirs([str(one), str(two)])

    assert one.exists()
    assert two.exists()


def test_get_record_path_raises_for_invalid_prefix(monkeypatch: pytest.MonkeyPatch):
    """Raise when prefix does not include user/institute/sample segments."""
    monkeypatch.setattr(filesystem_utils, "_id_sep", lambda: "-")
    monkeypatch.setattr(filesystem_utils, "_dest_dir", lambda: Path("C:/tmp"))

    with pytest.raises(ValueError, match="does not contain three segments"):
        filesystem_utils.get_record_path("invalid-prefix")


def test_get_record_path_uses_active_device_abbreviation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """Prefix sample folder with active device abbreviation when available."""
    monkeypatch.setattr(filesystem_utils, "_id_sep", lambda: "-")
    monkeypatch.setattr(filesystem_utils, "_dest_dir", lambda: tmp_path)
    monkeypatch.setattr(
        filesystem_utils,
        "_current_device",
        lambda: SimpleNamespace(metadata=SimpleNamespace(device_abbr="SEM")),
    )

    resolved = filesystem_utils.get_record_path("mus-ipat-sampleA")

    assert Path(resolved).name == "SEM-sampleA"


def test_current_device_returns_active_config_device(monkeypatch: pytest.MonkeyPatch):
    """Return device from active config helper."""
    sentinel_device = object()
    monkeypatch.setattr(
        filesystem_utils,
        "_active_config",
        lambda: SimpleNamespace(device=sentinel_device),
    )

    assert filesystem_utils._current_device() is sentinel_device  # noqa: SLF001


def test_move_item_removes_empty_placeholder(tmp_path: Path):
    """Replace empty destination placeholder file before moving source."""
    src = tmp_path / "src.txt"
    src.write_text("payload")
    dest = tmp_path / "dest.txt"
    dest.write_text("")

    filesystem_utils.move_item(src, dest)

    assert dest.read_text() == "payload"
    assert not src.exists()


def test_move_item_falls_back_to_shutil_move(tmp_path: Path, monkeypatch):
    """Fallback to shutil.move when Path.rename raises an OSError."""
    src = tmp_path / "src.txt"
    src.write_text("payload")
    dest = tmp_path / "dest.txt"
    moved = {}

    def raise_rename(self, target):
        raise OSError("rename failed")

    def fake_move(src_path, dest_path):
        moved["args"] = (src_path, dest_path)
        dest_path = Path(dest_path)
        dest_path.write_text(Path(src_path).read_text())
        Path(src_path).unlink()

    monkeypatch.setattr(Path, "rename", raise_rename)
    monkeypatch.setattr(shutil, "move", fake_move)

    filesystem_utils.move_item(src, dest)

    assert moved["args"] == (str(src), str(dest))
    assert dest.read_text() == "payload"


def test_move_item_removes_nonempty_destination_directory(tmp_path: Path):
    """Remove non-empty destination directory before renaming source path."""
    src = tmp_path / "src.txt"
    src.write_text("payload")
    dest = tmp_path / "dest-path"
    dest.mkdir()
    (dest / "child.txt").write_text("child")

    filesystem_utils.move_item(src, dest)

    assert dest.is_file()
    assert dest.read_text() == "payload"
    assert not src.exists()


def test_move_item_raises_when_fallback_move_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """Raise fallback exception after cleanup when shutil.move also fails."""
    src = tmp_path / "src.txt"
    src.write_text("payload")
    dest = tmp_path / "dest-path"
    dest.mkdir()
    (dest / "child.txt").write_text("child")

    def _raise_rename(self, target):  # type: ignore[no-untyped-def]
        raise OSError("rename failed")

    def _raise_move(_src: str, _dest: str) -> None:
        raise RuntimeError("fallback move failed")

    monkeypatch.setattr(Path, "rename", _raise_rename)
    monkeypatch.setattr(shutil, "move", _raise_move)

    with pytest.raises(RuntimeError, match="fallback move failed"):
        filesystem_utils.move_item(src, dest)


def test_move_item_fallback_cleans_nonempty_destination_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """Clean fallback destination directory state before invoking shutil.move."""
    src = tmp_path / "src.txt"
    src.write_text("payload")
    dest = tmp_path / "dest-path"
    moved = {}

    def _raise_rename_with_dest_creation(self, target):  # type: ignore[no-untyped-def]
        target_path = Path(target)
        target_path.mkdir(parents=True, exist_ok=True)
        (target_path / "child.txt").write_text("child")
        raise OSError("rename failed")

    def _fake_move(src_path: str, dest_path: str) -> None:
        moved["args"] = (src_path, dest_path)
        Path(dest_path).write_text(Path(src_path).read_text())
        Path(src_path).unlink()

    monkeypatch.setattr(Path, "rename", _raise_rename_with_dest_creation)
    monkeypatch.setattr(shutil, "move", _fake_move)

    filesystem_utils.move_item(src, dest)

    assert moved["args"] == (str(src), str(dest))
    assert dest.is_file()
    assert dest.read_text() == "payload"


def test_move_item_fallback_removes_empty_file_placeholder(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """Remove empty file placeholder in fallback path before shutil.move."""
    src = tmp_path / "src.txt"
    src.write_text("payload")
    dest = tmp_path / "dest.txt"
    moved = {}

    def _raise_rename_with_empty_dest(self, target):  # type: ignore[no-untyped-def]
        Path(target).write_text("")
        raise OSError("rename failed")

    def _fake_move(src_path: str, dest_path: str) -> None:
        moved["args"] = (src_path, dest_path)
        Path(dest_path).write_text(Path(src_path).read_text())
        Path(src_path).unlink()

    monkeypatch.setattr(Path, "rename", _raise_rename_with_empty_dest)
    monkeypatch.setattr(shutil, "move", _fake_move)

    filesystem_utils.move_item(src, dest)

    assert moved["args"] == (str(src), str(dest))
    assert dest.read_text() == "payload"
    assert not src.exists()


def test_remove_directory_if_empty_warns_on_nonempty(tmp_path: Path):
    """Keep directory in place and warn when it is not empty."""
    folder = tmp_path / "folder"
    folder.mkdir()
    (folder / "child.txt").write_text("data")

    filesystem_utils.remove_directory_if_empty(folder)

    assert folder.exists()


def test_remove_directory_if_empty_removes_empty_folder(tmp_path: Path):
    """Remove directory when no children remain."""
    folder = tmp_path / "folder"
    folder.mkdir()

    filesystem_utils.remove_directory_if_empty(folder)

    assert not folder.exists()


def test_load_persisted_records_invalid_json_returns_empty(tmp_path: Path, monkeypatch):
    """Return empty mapping when daily-records JSON cannot be parsed."""
    records_path = tmp_path / "records.json"
    records_path.write_text("{bad json")

    monkeypatch.setattr(filesystem_utils, "_daily_records_path", lambda: records_path)

    result = filesystem_utils.load_persisted_records()

    assert result == {}


def test_load_persisted_records_returns_localrecord_mapping(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """Load JSON payload into LocalRecord objects keyed by record id."""
    records_path = tmp_path / "records.json"
    payload = {
        "dev-usr-ipat-sample": LocalRecord(identifier="dev-usr-ipat-sample").to_dict()
    }
    records_path.write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr(filesystem_utils, "_daily_records_path", lambda: records_path)
    monkeypatch.setattr(filesystem_utils, "_id_sep", lambda: "-")

    result = filesystem_utils.load_persisted_records()

    assert set(result.keys()) == {"dev-usr-ipat-sample"}
    assert isinstance(result["dev-usr-ipat-sample"], LocalRecord)


def test_save_persisted_records_writes_json(tmp_path: Path, monkeypatch, config_service):
    """Serialize LocalRecord mapping to JSON file."""
    records_path = tmp_path / "records.json"
    monkeypatch.setattr(filesystem_utils, "_daily_records_path", lambda: records_path)

    record = LocalRecord(identifier="dev-user-inst-sample")

    filesystem_utils.save_persisted_records({"id": record})

    payload = json.loads(records_path.read_text())
    assert "id" in payload


def test_save_persisted_records_handles_write_failures(monkeypatch: pytest.MonkeyPatch):
    """Swallow write exceptions after logging when persistence path cannot be written."""

    class _BrokenPath:
        def write_text(self, _serialized: str, encoding: str = "utf-8") -> None:
            raise OSError("write denied")

        def __str__(self) -> str:
            return "broken.json"

    monkeypatch.setattr(filesystem_utils, "_daily_records_path", lambda: _BrokenPath())

    filesystem_utils.save_persisted_records({})


def test_move_to_record_folder_uses_record_path_factory(monkeypatch: pytest.MonkeyPatch):
    """Route move-to-record calls through record-path factory and move helper."""
    calls: dict[str, object] = {}

    monkeypatch.setattr(filesystem_utils, "get_record_path", lambda name: f"/records/{name}")
    monkeypatch.setattr(
        filesystem_utils,
        "move_item",
        lambda src, dest: calls.update({"src": src, "dest": dest}),
    )

    filesystem_utils.move_to_record_folder("C:/raw/file.txt", "prefix", ".txt")

    assert calls == {"src": "C:/raw/file.txt", "dest": "/records/prefix.txt"}
