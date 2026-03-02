"""Unit coverage for record persistence context assembly helpers."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from dpost.application.processing.record_persistence_context import (
    RecordPersistenceContext,
    build_record_persistence_context,
)


def test_build_record_persistence_context_requires_explicit_separator() -> None:
    """Reject persistence-context assembly when naming separator is omitted."""
    with pytest.raises(ValueError, match="id_separator must be provided explicitly"):
        build_record_persistence_context(
            records=object(),
            existing_record=None,
            filename_prefix="abc-ipat-sample",
            device=None,
            processor=object(),
            id_separator="",
            dest_dir=Path("C:/records"),
            current_device_provider=lambda: None,
            get_or_create_record_fn=lambda *_args: object(),
            apply_device_defaults_fn=lambda *_args: None,
            get_record_path_fn=lambda *_args, **_kwargs: "C:/records/path",
            generate_file_id_fn=lambda *_args, **_kwargs: "FILE-ID",
        )


def test_build_record_persistence_context_forwards_explicit_context() -> None:
    """Forward naming/storage context and resolved device values to helper seams."""
    device = SimpleNamespace(metadata=SimpleNamespace(device_abbr="SEM"))
    record = object()
    captured: dict[str, tuple[tuple[object, ...], dict[str, object]]] = {}

    context = build_record_persistence_context(
        records="records",
        existing_record=None,
        filename_prefix="abc-ipat-sample",
        device=device,
        processor="processor",
        id_separator="-",
        dest_dir=Path("C:/records"),
        current_device_provider=lambda: (_ for _ in ()).throw(
            AssertionError("provider should not be called when device is explicit")
        ),
        get_or_create_record_fn=lambda *args: captured.__setitem__(
            "record", (args, {})
        )
        or record,
        apply_device_defaults_fn=lambda *args: captured.__setitem__(
            "defaults", (args, {})
        ),
        get_record_path_fn=lambda *args, **kwargs: captured.__setitem__(
            "record_path", (args, kwargs)
        )
        or "C:/records/path",
        generate_file_id_fn=lambda *args, **kwargs: captured.__setitem__(
            "file_id", (args, kwargs)
        )
        or "FILE-ID",
    )

    assert context == RecordPersistenceContext(
        record=record,
        processor="processor",
        record_path="C:/records/path",
        file_id="FILE-ID",
    )
    assert captured["record"][0] == ("records", None, "abc-ipat-sample", device)
    assert captured["defaults"][0] == (record, device)
    assert captured["record_path"] == (
        ("abc-ipat-sample", "SEM"),
        {
            "id_separator": "-",
            "dest_dir": Path("C:/records"),
            "current_device": device,
        },
    )
    assert captured["file_id"] == (
        ("abc-ipat-sample", "SEM"),
        {
            "id_separator": "-",
            "current_device": device,
        },
    )
