from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from ipat_watchdog.core.records.local_record import LocalRecord
import pytest

from ipat_watchdog.core.processing.file_process_manager import FileProcessManager
from ipat_watchdog.core.storage.filesystem_utils import get_record_path, init_dirs
from ipat_watchdog.device_plugins.utm_zwick.settings import build_config as build_utm_config
from ipat_watchdog.pc_plugins.test_pc.settings import build_config as build_pc_config
from tests.helpers.fake_sync import DummySyncManager
from tests.helpers.fake_ui import HeadlessUI
from tests.helpers.fake_session import FakeSessionManager
from ipat_watchdog.core.config import init_config, reset_service


@pytest.fixture
def utm_processing_manager(tmp_path):
    root = tmp_path / "sandbox"
    overrides = {
        "app_dir": root / "App",
        "watch_dir": root / "Upload",
        "dest_dir": root / "Data",
        "rename_dir": root / "Data" / "00_To_Rename",
        "exceptions_dir": root / "Data" / "01_Exceptions",
        "daily_records_json": root / "records.json",
    }

    pc_config = build_pc_config(override_paths=overrides)
    utm_config = build_utm_config()
    utm_config = replace(
        utm_config,
        watcher=replace(utm_config.watcher, poll_seconds=0.05, stable_cycles=1, max_wait_seconds=5.0),
    )

    service = init_config(pc_config, [utm_config])
    init_dirs()

    ui = HeadlessUI()
    sync = DummySyncManager(ui)
    session = FakeSessionManager(interactions=ui, scheduler=ui)
    fpm = FileProcessManager(
        interactions=ui,
        sync_manager=sync,
        session_manager=session,
        config_service=service,
    )
    try:
        yield fpm, ui
    finally:
        reset_service()


def _emit_and_process(
    fpm: FileProcessManager,
    watch_dir: Path,
    prefix: str,
    order: list[str],
    payloads: dict[str, str] | None = None,
) -> Path:
    """
    order items can be:
      - "zs2"        -> {prefix}.zs2
      - "csv"        -> {prefix}.csv
      - "txt-<NN>"   -> {prefix}-<NN>.txt (e.g., "txt-01", "txt-02")

    Returns the record directory path.
    """
    payloads = payloads or {}
    for token in order:
        if token == "zs2":
            p = watch_dir / f"{prefix}.zs2"
            p.write_text(payloads.get("zs2", "raw-zs2"))
        elif token == "csv":
            p = watch_dir / f"{prefix}.csv"
            p.write_text(payloads.get("csv", "final-results"))
        elif token.startswith("txt-"):
            nn = token.split("-", 1)[1]
            p = watch_dir / f"{prefix}-{nn}.txt"
            p.write_text(payloads.get(token, f"snapshot-{nn}"))
        else:
            raise ValueError(f"Unknown token in order: {token}")
        fpm.process_item(str(p))

    return Path(get_record_path(prefix, "UTM"))


def _expect_exists(record_dir: Path, *names: str) -> None:
    for name in names:
        path = record_dir / name
        assert path.exists(), f"Expected file not found: {path}"


def test_end_to_end_series_processing_with_txt_and_csv(utm_processing_manager, tmp_settings):
    fpm, ui = utm_processing_manager
    prefix = "usr-ipat-tensileA"

    # zs2 and txt snapshots arrive before csv (finalizes on csv)
    record_dir = _emit_and_process(
        fpm,
        tmp_settings.WATCH_DIR,
        prefix,
        order=["zs2", "txt-01", "txt-02", "csv"],
    )

    # Non-overwriting unique names now expected for final artefacts.
    # First arrival should still create initial numbered variants (..-01.*)
    zs2_candidates = sorted(record_dir.glob("UTM-tensileA-*.zs2"))
    csv_candidates = sorted(record_dir.glob("UTM-tensileA_results-*.csv"))
    assert zs2_candidates, "Expected at least one unique .zs2 artefact"
    assert csv_candidates, "Expected at least one unique .csv artefact"
    # The first ones should end with -01 by convention of get_unique_filename
    assert any(p.stem.endswith("-01") for p in zs2_candidates), "Missing initial -01 .zs2"
    assert any(p.stem.endswith("-01") for p in csv_candidates), "Missing initial -01 .csv"

    # We keep all TXT snapshots. Filenames are generated via get_unique_filename,
    # so don't assume a "-NN" scheme; just ensure we have at least two with the right prefix/suffix.
    tests = sorted(record_dir.glob("UTM-tensileA_tests*.txt"))
    assert len(tests) >= 2, f"Expected >= 2 text snapshots, found: {len(tests)}"

    # Optional sanity: ensure snapshot filenames are unique (no accidental overwrite)
    assert len({p.name for p in tests}) == len(tests), "TXT snapshot names should be unique"


def test_repeat_series_creates_additional_unique_files(utm_processing_manager, tmp_settings):
    fpm, _ui = utm_processing_manager
    prefix = "usr-ipat-tensileA"

    record_dir = _emit_and_process(
        fpm,
        tmp_settings.WATCH_DIR,
        prefix,
        order=["zs2", "txt-01", "txt-02", "csv"],
    )

    record: LocalRecord = next(iter(fpm.records.persist_records_dict.values()))
    preexisting_files = set(record.files_uploaded.keys())
    assert preexisting_files
    assert record.files_require_force == set()

    fpm.records.sync_records_to_database()
    sync_manager = fpm.records.sync
    assert sync_manager.synced_records
    assert record.all_files_uploaded()

    second_dir = _emit_and_process(
        fpm,
        tmp_settings.WATCH_DIR,
        prefix,
        order=["zs2", "txt-03", "csv"],
        payloads={
            "zs2": "raw-zs2-second",
            "txt-03": "snapshot-03-second",
            "csv": "final-results-second",
        },
    )
    assert second_dir == record_dir

    # After second series, we expect additional uniquely numbered artefacts, not overwrites.
    zs2_files = sorted(record_dir.glob("UTM-tensileA-*.zs2"))
    csv_files = sorted(record_dir.glob("UTM-tensileA_results-*.csv"))
    assert len(zs2_files) >= 2, "Expected at least two .zs2 versions after repeat series"
    assert len(csv_files) >= 2, "Expected at least two .csv versions after repeat series"

    # Ensure numbering increments (collect numeric suffixes)
    import re as _re
    suffix_pattern = _re.compile(r".*-(\d+)$")
    zs2_nums = sorted({int(suffix_pattern.match(p.stem).group(1)) for p in zs2_files if suffix_pattern.match(p.stem)})
    csv_nums = sorted({int(suffix_pattern.match(p.stem).group(1)) for p in csv_files if suffix_pattern.match(p.stem)})
    assert zs2_nums == list(range(1, len(zs2_nums)+1)), f"Unexpected gap or numbering in zs2 files: {zs2_nums}"
    assert csv_nums == list(range(1, len(csv_nums)+1)), f"Unexpected gap or numbering in csv files: {csv_nums}"

    # Previously we flagged force overwrites; now earlier files remain uploaded, new ones appear as not uploaded yet.
    # Validate preexisting files still tracked, and new files added with uploaded=False without forcing previous ones.
    current_files = set(record.files_uploaded.keys())
    new_files = current_files - preexisting_files
    assert new_files, "Expected newly created unique artefacts to be tracked"
    # Previously uploaded files are re-registered, so they require force; new ones should not be in force set yet.
    assert preexisting_files.issubset(record.files_require_force), "Previously uploaded files should now require force"
    assert not (new_files & record.files_require_force), "New unique files should not require force initially"
    # New artefacts should have uploaded flag False (pending upload)
    assert all(record.files_uploaded[f] is False for f in new_files), "New unique files should be pending upload"
