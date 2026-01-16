from __future__ import annotations

import json
import shutil
from pathlib import Path

from ipat_watchdog.core.records.local_record import LocalRecord
from ipat_watchdog.core.storage import filesystem_utils


def test_move_item_removes_empty_placeholder(tmp_path: Path):
    src = tmp_path / "src.txt"
    src.write_text("payload")
    dest = tmp_path / "dest.txt"
    dest.write_text("")

    filesystem_utils.move_item(src, dest)

    assert dest.read_text() == "payload"
    assert not src.exists()


def test_move_item_falls_back_to_shutil_move(tmp_path: Path, monkeypatch):
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


def test_remove_directory_if_empty_warns_on_nonempty(tmp_path: Path):
    folder = tmp_path / "folder"
    folder.mkdir()
    (folder / "child.txt").write_text("data")

    filesystem_utils.remove_directory_if_empty(folder)

    assert folder.exists()


def test_load_persisted_records_invalid_json_returns_empty(tmp_path: Path, monkeypatch):
    records_path = tmp_path / "records.json"
    records_path.write_text("{bad json")

    monkeypatch.setattr(filesystem_utils, "_daily_records_path", lambda: records_path)

    result = filesystem_utils.load_persisted_records()

    assert result == {}


def test_save_persisted_records_writes_json(tmp_path: Path, monkeypatch):
    records_path = tmp_path / "records.json"
    monkeypatch.setattr(filesystem_utils, "_daily_records_path", lambda: records_path)

    record = LocalRecord(identifier="dev-user-inst-sample")

    filesystem_utils.save_persisted_records({"id": record})

    payload = json.loads(records_path.read_text())
    assert "id" in payload
