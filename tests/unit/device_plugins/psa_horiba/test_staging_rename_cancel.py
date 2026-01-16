from __future__ import annotations

from pathlib import Path

from ipat_watchdog.core.interactions.messages import InfoMessages
from ipat_watchdog.core.processing.rename_flow import RenameService
from ipat_watchdog.device_plugins.psa_horiba.file_processor import FileProcessorPSAHoriba
from ipat_watchdog.device_plugins.psa_horiba.settings import build_config
from tests.helpers.fake_ui import HeadlessUI


def _write_pair(watch_dir: Path, stem: str, probenname: str | None = None, ngb_payload: bytes = b"ngb") -> tuple[Path, Path]:
    ngb = watch_dir / f"{stem}.ngb"
    ngb.write_bytes(ngb_payload)
    csv = watch_dir / f"{stem}.csv"
    if probenname is None:
        csv.write_text("Probenname\tSample\nX(mm)\t1\n", encoding="utf-8")
    else:
        csv.write_text(f"Probenname;{probenname}\nX(mm);1\n", encoding="utf-8")
    return csv, ngb


def test_staged_folder_moves_as_one_on_rename_cancel(tmp_settings):
    # Arrange: build processor and a batch with one bucket pair + one sentinel pair
    proc = FileProcessorPSAHoriba(build_config())
    watch_dir = tmp_settings.WATCH_DIR
    watch_dir.mkdir(parents=True, exist_ok=True)

    # Bucket pair (NGB -> CSV)
    _, ngb_first = _write_pair(watch_dir, "bucket1", probenname="BatchA", ngb_payload=b"a")
    assert proc.device_specific_preprocessing(str(ngb_first)) is None
    # The CSV arrives afterwards to form the pair
    csv_first = watch_dir / "bucket1.csv"
    assert csv_first.exists()
    assert proc.device_specific_preprocessing(str(csv_first)) is None

    # Sentinel pair (CSV -> NGB) triggers flush and staging
    sentinel_csv = watch_dir / "sentinel.csv"
    sentinel_csv.write_text("Probenname;FINAL\nX(mm);2\n", encoding="utf-8")
    assert proc.device_specific_preprocessing(str(sentinel_csv)) is None

    sentinel_ngb = watch_dir / "sentinel.ngb"
    sentinel_ngb.write_bytes(b"b")

    staged = proc.device_specific_preprocessing(str(sentinel_ngb))
    assert staged is not None, "Expected a staging folder path to be advertised"
    stage_dir = Path(staged.effective_path)
    assert stage_dir.is_dir()
    assert stage_dir.name.startswith("FINAL.__staged__")

    # Act: simulate a rename cancellation; the whole staging folder should be moved to rename
    ui = HeadlessUI()
    ui.show_rename_dialog_return = None  # explicit cancel
    renamer = RenameService(ui)

    renamer.send_to_manual_bucket(str(stage_dir), stage_dir.stem, "")

    # Assert: info message shown and the entire staging folder moved under rename dir
    assert ui.calls["show_info"][-1] == (InfoMessages.OPERATION_CANCELLED, InfoMessages.MOVED_TO_RENAME)

    # The original stage dir should no longer exist
    assert not stage_dir.exists()

    # Find the moved folder in the configured rename directory
    moved = [p for p in tmp_settings.RENAME_DIR.iterdir() if p.name.startswith(stage_dir.stem)]
    assert len(moved) == 1, f"Expected exactly one moved staging folder, found: {moved}"
    moved_dir = moved[0]
    assert moved_dir.is_dir()

    # Contents (original CSV+NGB) should be present together in the moved folder
    names = sorted(p.name for p in moved_dir.iterdir())
    # We expect two CSVs and two NGBs (originals), not zipped yet
    assert any(name.endswith(".csv") for name in names)
    assert any(name.endswith(".ngb") for name in names)
