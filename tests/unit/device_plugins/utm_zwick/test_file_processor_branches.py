"""Branch-focused tests for UTM Zwick processor helper paths."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from dpost.device_plugins.utm_zwick.file_processor import (
    FileProcessorUTMZwick,
    _SeriesState,
)
from dpost.device_plugins.utm_zwick.settings import build_config


def test_configure_runtime_context_sets_missing_storage_fields_only() -> None:
    """Populate missing runtime naming/storage context and preserve existing values."""
    processor = FileProcessorUTMZwick(build_config())
    current_device = object()

    processor.configure_runtime_context(
        id_separator="__",
        dest_dir="C:/records",
        current_device=current_device,
    )

    assert processor._id_separator == "__"  # noqa: SLF001
    assert processor._dest_dir == "C:/records"  # noqa: SLF001
    assert processor._current_device is current_device  # noqa: SLF001

    existing_device = object()
    processor._id_separator = "-"  # noqa: SLF001
    processor._dest_dir = "C:/existing"  # noqa: SLF001
    processor._current_device = existing_device  # noqa: SLF001
    processor.configure_runtime_context(
        id_separator="++",
        dest_dir="C:/ignored",
        current_device=object(),
    )

    assert processor._id_separator == "-"  # noqa: SLF001
    assert processor._dest_dir == "C:/existing"  # noqa: SLF001
    assert processor._current_device is existing_device  # noqa: SLF001


def test_preprocessing_returns_ttl_ready_zs2_path(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Return passthrough for TTL-ready series before processing current event."""
    processor = FileProcessorUTMZwick(build_config())
    ready_zs2 = tmp_path / "ready.zs2"
    ready_zs2.write_text("raw")
    ready_state = _SeriesState(
        series_key="ready",
        sample="ready",
        last_zs2=ready_zs2,
        last_update=datetime.now() - timedelta(seconds=999),
    )
    monkeypatch.setattr(processor, "_find_ttl_ready_locked", lambda: ready_state)

    result = processor.device_specific_preprocessing(str(tmp_path / "incoming.zs2"))

    assert result is not None
    assert result.effective_path == str(ready_zs2)


def test_probe_and_appendable_branches(tmp_path: Path) -> None:
    """Cover probe match/mismatch branches and appendability helper."""
    processor = FileProcessorUTMZwick(build_config())
    zs2 = tmp_path / "sample.zs2"
    zs2.write_text("raw")
    xlsx = tmp_path / "sample.xlsx"
    xlsx.write_text("xlsx")
    txt = tmp_path / "sample.txt"
    txt.write_text("txt")

    assert processor.probe_file(str(zs2)).is_match() is True
    assert processor.probe_file(str(xlsx)).is_match() is True
    xlsx.unlink()
    xlsx_no_sibling = tmp_path / "orphan.xlsx"
    xlsx_no_sibling.write_text("xlsx")
    assert processor.probe_file(str(xlsx_no_sibling)).is_mismatch() is True
    assert processor.probe_file(str(txt)).is_mismatch() is True
    assert processor.is_appendable(None, "prefix", ".xlsx") is True


def test_find_ttl_ready_locked_skips_nonready_states_and_returns_stale_zs2() -> None:
    """Skip sentinel/non-zs2 states and return first stale pending zs2 series."""
    processor = FileProcessorUTMZwick(build_config())
    processor.device_config.batch.ttl_seconds = 5
    now = datetime.now()
    state_with_sentinel = _SeriesState(
        series_key="sentinel",
        sample="s",
        sentinel_xlsx=Path("s.xlsx"),
        last_zs2=Path("s.zs2"),
        last_update=now - timedelta(seconds=10),
    )
    state_missing_zs2 = _SeriesState(
        series_key="missing",
        sample="m",
        last_zs2=None,
        last_update=now - timedelta(seconds=10),
    )
    state_ready = _SeriesState(
        series_key="ready",
        sample="r",
        last_zs2=Path("r.zs2"),
        last_update=now - timedelta(seconds=10),
    )
    processor._series = {
        "sentinel": state_with_sentinel,
        "missing": state_missing_zs2,
        "ready": state_ready,
    }

    selected = processor._find_ttl_ready_locked()

    assert selected is state_ready


def test_move_staged_artifact_returns_early_for_none_or_missing_source(
    tmp_path: Path,
) -> None:
    """Skip movement when source path is absent or does not exist."""
    record_dir = tmp_path / "record"
    record_dir.mkdir()

    FileProcessorUTMZwick._move_staged_artifact(
        source=None,
        record_dir=record_dir,
        filename_prefix="prefix",
        success_label="ok",
        failure_label="fail",
    )
    FileProcessorUTMZwick._move_staged_artifact(
        source=tmp_path / "missing.zs2",
        record_dir=record_dir,
        filename_prefix="prefix",
        success_label="ok",
        failure_label="fail",
    )


def test_move_staged_artifact_logs_warning_on_move_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Suppress move exceptions so staged processing can continue."""
    source = tmp_path / "sample.zs2"
    source.write_text("raw")
    record_dir = tmp_path / "record"
    record_dir.mkdir()
    monkeypatch.setattr(
        "dpost.device_plugins.utm_zwick.file_processor.get_unique_filename",
        lambda _record_dir, _prefix, _suffix, **_kwargs: str(
            record_dir / "prefix-01.zs2"
        ),
    )
    monkeypatch.setattr(
        "dpost.device_plugins.utm_zwick.file_processor.move_item",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("move failed")),
    )

    FileProcessorUTMZwick._move_staged_artifact(
        source=source,
        record_dir=record_dir,
        filename_prefix="prefix",
        success_label="raw",
        failure_label="raw",
    )
