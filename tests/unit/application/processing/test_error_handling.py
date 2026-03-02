from __future__ import annotations


from dpost.application.interactions import WarningMessages
from dpost.application.processing import error_handling
from tests.helpers.fake_ui import HeadlessUI


def test_safe_move_to_exception_ignores_missing(monkeypatch):
    calls = []

    def raise_missing(path_like, prefix, extension, **kwargs):
        calls.append((path_like, prefix, extension, kwargs))
        raise FileNotFoundError("missing")

    monkeypatch.setattr(error_handling, "move_to_exception_folder", raise_missing)

    error_handling.safe_move_to_exception("missing.txt", prefix="prefix", extension=".txt")

    assert calls == [
        (
            "missing.txt",
            "prefix",
            ".txt",
            {"base_dir": ".", "id_separator": "-"},
        )
    ]


def test_safe_move_to_exception_forwards_explicit_exception_context(monkeypatch):
    calls = []

    def record_move(path_like, prefix, extension, **kwargs):
        calls.append((path_like, prefix, extension, kwargs))

    monkeypatch.setattr(error_handling, "move_to_exception_folder", record_move)

    error_handling.safe_move_to_exception(
        "sample.txt",
        prefix="prefix",
        extension=".txt",
        exception_dir="C:/Exceptions",
        id_separator="__",
    )

    assert calls == [
        (
            "sample.txt",
            "prefix",
            ".txt",
            {"base_dir": "C:/Exceptions", "id_separator": "__"},
        )
    ]


def test_move_to_exception_and_inform_warns_and_handles_preprocessed(tmp_path, monkeypatch):
    ui = HeadlessUI()
    src = tmp_path / "src.txt"
    src.write_text("data")
    preprocessed = tmp_path / "pre.txt"
    preprocessed.write_text("data")

    calls = []

    def record_move(path_like, prefix, extension):
        calls.append((path_like, prefix, extension))

    monkeypatch.setattr(error_handling, "safe_move_to_exception", record_move)

    error_handling.move_to_exception_and_inform(
        ui,
        str(src),
        "prefix",
        ".txt",
        "Warning",
        "message",
        preprocessed_src_path=str(preprocessed),
    )

    assert ui.warnings == [("Warning", "message")]
    assert ui.errors == []
    assert calls == [
        (str(src), "prefix", ".txt"),
        (str(preprocessed), "prefix", ".txt"),
    ]


def test_move_to_exception_and_inform_errors(monkeypatch):
    ui = HeadlessUI()
    calls = []

    def record_move(path_like, prefix, extension):
        calls.append((path_like, prefix, extension))

    monkeypatch.setattr(error_handling, "safe_move_to_exception", record_move)

    error_handling.move_to_exception_and_inform(
        ui,
        "sample.txt",
        "prefix",
        ".txt",
        "Error",
        "bad",
    )

    assert ui.errors == [("Error", "bad")]
    assert ui.warnings == []
    assert calls == [("sample.txt", "prefix", ".txt")]


def test_handle_invalid_datatype_uses_warning_message(tmp_path, monkeypatch):
    ui = HeadlessUI()
    src = tmp_path / "sample.txt"
    src.write_text("data")

    def record_move(path_like, prefix, extension):
        return None

    monkeypatch.setattr(error_handling, "safe_move_to_exception", record_move)

    error_handling.handle_invalid_datatype(ui, str(src), "prefix", ".txt")

    assert ui.warnings == [("Warning", WarningMessages.INVALID_DATA_TYPE_DETAILS)]
