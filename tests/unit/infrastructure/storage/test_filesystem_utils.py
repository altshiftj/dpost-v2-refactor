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


def test_get_record_path_accepts_explicit_context_without_global_config(tmp_path: Path):
    """Allow callers to provide separator/destination/device context explicitly."""
    explicit_device = SimpleNamespace(metadata=SimpleNamespace(device_abbr="XRD"))

    resolved = filesystem_utils.get_record_path(
        "mus__ipat__sampleA",
        id_separator="__",
        dest_dir=tmp_path,
        current_device=explicit_device,
    )

    resolved_path = Path(resolved)
    assert resolved_path.parent.name == "MUS"
    assert resolved_path.parent.parent.name == "IPAT"
    assert resolved_path.name == "XRD-sampleA"


def test_current_device_returns_active_config_device(monkeypatch: pytest.MonkeyPatch):
    """Return device from active config helper."""
    sentinel_device = object()
    monkeypatch.setattr(
        filesystem_utils,
        "_active_config",
        lambda: SimpleNamespace(device=sentinel_device),
    )

    assert filesystem_utils._current_device() is sentinel_device  # noqa: SLF001


def test_exceptions_dir_returns_active_config_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return exceptions directory from active config wrapper."""
    sentinel_path = Path("C:/tmp/exceptions")
    monkeypatch.setattr(
        filesystem_utils,
        "_active_config",
        lambda: SimpleNamespace(paths=SimpleNamespace(exceptions_dir=sentinel_path)),
    )

    assert filesystem_utils._exceptions_dir() == sentinel_path  # noqa: SLF001


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


def test_get_unique_filename_accepts_explicit_separator(tmp_path: Path) -> None:
    """Sequence parsing should support explicit separators without ambient config."""
    directory = tmp_path / "records"
    directory.mkdir()
    (directory / "prefix__01.txt").write_text("1")
    (directory / "prefix__02.txt").write_text("2")

    resolved = filesystem_utils.get_unique_filename(
        str(directory),
        "prefix",
        ".txt",
        id_separator="__",
    )

    assert Path(resolved).name == "prefix__03.txt"


@pytest.mark.parametrize("func_name", ["get_rename_path", "get_exception_path"])
def test_unique_path_helpers_accept_explicit_separator(
    tmp_path: Path,
    func_name: str,
) -> None:
    """Rename/exception path helpers should forward explicit separators."""
    base = tmp_path / "base"
    base.mkdir()
    (base / "item__01.csv").write_text("1")
    helper = getattr(filesystem_utils, func_name)

    resolved = helper("item.csv", base_dir=str(base), id_separator="__")

    assert Path(resolved).name == "item__02.csv"


def test_get_exception_path_uses_default_exceptions_dir_when_not_provided(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fallback exception path helper should use active exceptions dir wrapper."""
    exceptions_dir = tmp_path / "exceptions"
    exceptions_dir.mkdir()
    (exceptions_dir / "item-01.csv").write_text("1")

    monkeypatch.setattr(filesystem_utils, "_exceptions_dir", lambda: exceptions_dir)
    monkeypatch.setattr(filesystem_utils, "_id_sep", lambda: "-")

    resolved = filesystem_utils.get_exception_path("item.csv")

    assert Path(resolved).name == "item-02.csv"


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


def test_move_to_exception_folder_accepts_explicit_base_dir_and_separator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exception moves should support explicit path context without runtime globals."""
    src = tmp_path / "sample.txt"
    src.write_text("data")
    dest_dir = tmp_path / "exceptions"
    calls: dict[str, tuple[tuple[object, ...], dict[str, object]]] = {}

    monkeypatch.setattr(
        filesystem_utils,
        "get_exception_path",
        lambda *args, **kwargs: calls.__setitem__("path", (args, kwargs))
        or str(dest_dir / "sample-01.txt"),
    )
    monkeypatch.setattr(
        filesystem_utils,
        "move_item",
        lambda *args, **kwargs: calls.__setitem__("move", (args, kwargs)),
    )

    filesystem_utils.move_to_exception_folder(
        str(src),
        base_dir=str(dest_dir),
        id_separator="__",
    )

    path_args, path_kwargs = calls["path"]
    move_args, _move_kwargs = calls["move"]
    assert path_args == ("sample.txt",)
    assert path_kwargs == {"base_dir": str(dest_dir), "id_separator": "__"}
    assert move_args == (str(src), str(dest_dir / "sample-01.txt"))


def test_move_to_rename_folder_accepts_explicit_base_dir_and_separator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rename moves should support explicit path context without runtime globals."""
    src = tmp_path / "sample.txt"
    src.write_text("data")
    dest_dir = tmp_path / "rename"
    calls: dict[str, tuple[tuple[object, ...], dict[str, object]]] = {}

    monkeypatch.setattr(
        filesystem_utils,
        "get_rename_path",
        lambda *args, **kwargs: calls.__setitem__("path", (args, kwargs))
        or str(dest_dir / "sample-01.txt"),
    )
    monkeypatch.setattr(
        filesystem_utils,
        "move_item",
        lambda *args, **kwargs: calls.__setitem__("move", (args, kwargs)),
    )

    filesystem_utils.move_to_rename_folder(
        str(src),
        "sample",
        ".txt",
        base_dir=str(dest_dir),
        id_separator="__",
    )

    path_args, path_kwargs = calls["path"]
    move_args, _move_kwargs = calls["move"]
    assert path_args == ("sample.txt",)
    assert path_kwargs == {"base_dir": str(dest_dir), "id_separator": "__"}
    assert move_args == (str(src), str(dest_dir / "sample-01.txt"))


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


def test_load_and_save_persisted_records_accept_explicit_json_path(tmp_path: Path) -> None:
    """Persistence helpers should work with explicit paths/separators and no patches."""
    records_path = tmp_path / "records.json"
    record = LocalRecord(identifier="dev__usr__ipat__sample", id_separator="__")

    filesystem_utils.save_persisted_records({"id": record}, json_path=records_path)
    loaded = filesystem_utils.load_persisted_records(
        json_path=records_path,
        id_separator="__",
    )

    assert set(loaded.keys()) == {"id"}
    assert loaded["id"].identifier == "dev__usr__ipat__sample"
    assert loaded["id"].id_separator == "__"


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
