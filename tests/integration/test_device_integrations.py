from __future__ import annotations

from dataclasses import dataclass
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable

import pytest

import dpost.plugins.system as plugin_system
from dpost.application.config import (
    DeviceConfig,
    PCConfig,
    PathSettings,
)
from dpost.application.config.context import init_config, reset_service
from dpost.application.processing.file_process_manager import FileProcessManager
from dpost.application.processing.stability_tracker import (
    FileStabilityTracker,
    StabilityOutcome,
)
from dpost.application.runtime.device_watchdog_app import DeviceWatchdogApp
from dpost.device_plugins.dsv_horiba.settings import (
    build_config as build_dsv_config,
)
from dpost.device_plugins.erm_hioki.settings import (
    build_config as build_hioki_config,
)
from dpost.device_plugins.extr_haake.settings import (
    build_config as build_extr_config,
)
from dpost.device_plugins.psa_horiba.settings import (
    build_config as build_psa_config,
)
from dpost.device_plugins.rhe_kinexus.settings import (
    build_config as build_kinexus_config,
)
from dpost.device_plugins.rmx_eirich_el1.settings import (
    build_config as build_eirich_el1_config,
)
from dpost.device_plugins.rmx_eirich_r01.settings import (
    build_config as build_eirich_r01_config,
)
from dpost.device_plugins.sem_phenomxl2.settings import (
    build_config as build_sem_config,
)
from dpost.device_plugins.utm_zwick.settings import (
    build_config as build_utm_config,
)
from dpost.infrastructure.storage.filesystem_utils import init_dirs
from dpost.plugins.system import PluginLoader
from tests.helpers.fake_observer import FakeObserver
from tests.helpers.fake_sync import DummySyncManager
from tests.helpers.fake_ui import HeadlessUI
from tests.helpers.task_runner import drain_scheduled_tasks


@dataclass(frozen=True)
class SeededInputs:
    staged: tuple[Path, ...]
    queued: tuple[Path, ...]


@dataclass(frozen=True)
class DeviceSpec:
    name: str
    seed_inputs: Callable[[Path], SeededInputs]
    assert_outputs: Callable[[Path], None]
    rename_inputs: tuple[dict[str, str], ...] = ()


def _stable_immediately(self) -> StabilityOutcome:
    return StabilityOutcome(path=self.file_path, stable=True)


def _build_device_configs() -> list[DeviceConfig]:
    return [
        build_eirich_el1_config(),
        build_eirich_r01_config(),
        build_utm_config(),
        build_sem_config(),
        build_psa_config(),
        build_kinexus_config(),
        build_dsv_config(),
        build_hioki_config(),
        build_extr_config(),
    ]


def _build_uber_config(
    tmp_path: Path,
) -> tuple[PCConfig, list[DeviceConfig], PathSettings]:
    root = tmp_path / "sandbox"
    paths = PathSettings(
        app_dir=root / "App",
        watch_dir=root / "Upload",
        dest_dir=root / "Data",
        rename_dir=root / "Data" / "00_To_Rename",
        exceptions_dir=root / "Data" / "01_Exceptions",
        daily_records_json=root / "records.json",
    )
    device_configs = _build_device_configs()
    pc_config = PCConfig(
        identifier="uber_pc",
        name="UBER_PC",
        location="Test Lab",
        paths=paths,
        active_device_plugins=tuple(cfg.identifier for cfg in device_configs),
    )
    return pc_config, device_configs, paths


def _setup_app(
    tmp_path: Path, monkeypatch
) -> tuple[DeviceWatchdogApp, HeadlessUI, DummySyncManager, PathSettings]:
    _silence_file_logging(monkeypatch)
    monkeypatch.setattr(FileStabilityTracker, "wait", _stable_immediately)
    observer_stub = FakeObserver()
    loader = PluginLoader(load_entrypoints=False, load_builtins=False)
    monkeypatch.setattr(plugin_system, "_PLUGIN_LOADER_SINGLETON", loader)

    pc_config, device_configs, paths = _build_uber_config(tmp_path)
    config_service = init_config(pc_config, device_configs)
    init_dirs([str(path) for path in config_service.current.directory_list])

    ui = HeadlessUI()
    sync = DummySyncManager(ui)
    app = DeviceWatchdogApp(
        ui=ui,
        sync_manager=sync,
        config_service=config_service,
        file_process_manager_cls=FileProcessManager,
        observer_factory=lambda: observer_stub,
    )
    app.initialize()
    return app, ui, sync, paths


def _silence_file_logging(monkeypatch) -> None:
    """Avoid writing to the shared C:\\Watchdog log during tests."""
    import dpost.infrastructure.logging as logger_mod

    def _setup_logger_no_file(name: str = "watchdog") -> logging.Logger:
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        if not logger.handlers:
            logger.addHandler(logging.NullHandler())
        return logger

    monkeypatch.setattr(logger_mod, "setup_logger", _setup_logger_no_file)

    for logger_name in list(logging.Logger.manager.loggerDict):
        if not isinstance(logger_name, str) or not logger_name.startswith("dpost"):
            continue
        logger = logging.getLogger(logger_name)
        for handler in list(logger.handlers):
            if isinstance(handler, RotatingFileHandler):
                logger.removeHandler(handler)
                handler.close()


def _record_dir(
    dest_dir: Path, institute: str, user: str, device_abbr: str, sample: str
) -> Path:
    return dest_dir / institute.upper() / user.upper() / f"{device_abbr}-{sample}"


def _assert_single_suffix(record_dir: Path, suffix: str) -> None:
    matches = list(record_dir.glob(f"*{suffix}"))
    assert (
        len(matches) == 1
    ), f"Expected 1 '{suffix}' file in {record_dir}, found {matches}"


def _assert_min_suffix(record_dir: Path, suffix: str, minimum: int) -> None:
    matches = list(record_dir.glob(f"*{suffix}"))
    assert (
        len(matches) >= minimum
    ), f"Expected >= {minimum} '{suffix}' files in {record_dir}, found {matches}"


def _seed_extr_haake(watch_dir: Path) -> SeededInputs:
    path = watch_dir / "usr-ipat-extr1.xlsm"
    path.write_text("excel export", encoding="utf-8")
    return SeededInputs(staged=(), queued=(path,))


def _assert_extr_haake(dest_dir: Path) -> None:
    record_dir = _record_dir(dest_dir, "ipat", "usr", "EXTR", "extr1")
    assert record_dir.exists()
    _assert_single_suffix(record_dir, ".xlsm")


def _seed_hioki(watch_dir: Path) -> SeededInputs:
    path = watch_dir / "usr-ipat-hioki.xlsx"
    path.write_text("hioki export", encoding="utf-8")
    return SeededInputs(staged=(), queued=(path,))


def _assert_hioki(dest_dir: Path) -> None:
    record_dir = _record_dir(dest_dir, "ipat", "usr", "ERM", "hioki")
    assert record_dir.exists()
    _assert_single_suffix(record_dir, ".xlsx")


def _seed_dsv(watch_dir: Path) -> SeededInputs:
    wdb = watch_dir / "usr-ipat-dsv1.wdb"
    wdk = watch_dir / "usr-ipat-dsv1.wdk"
    wdp = watch_dir / "usr-ipat-dsv1.wdp"
    txt = watch_dir / "usr-ipat-dsv1.txt"
    for path in (wdb, wdk, wdp):
        path.write_bytes(b"raw")
    txt.write_text(
        "Dissolution release rpm medium horiba",
        encoding="utf-8",
    )
    return SeededInputs(staged=(wdb, wdk, wdp), queued=(txt,))


def _assert_dsv(dest_dir: Path) -> None:
    record_dir = _record_dir(dest_dir, "ipat", "usr", "DSV", "dsv1")
    assert record_dir.exists()
    zip_path = record_dir / "DSV-dsv1_raw_data.zip"
    assert zip_path.exists(), f"Expected raw archive at {zip_path}"
    _assert_min_suffix(record_dir, ".txt", 1)


def _seed_psa(watch_dir: Path) -> SeededInputs:
    csv_path = watch_dir / "usr-ipat-psa1.csv"
    ngb_path = watch_dir / "usr-ipat-psa1.ngb"
    csv_path.write_text(
        "Probenname;usr-ipat-psa1\nHoriba Partica LA-960\nDiameter;1\n",
        encoding="utf-8",
    )
    ngb_path.write_bytes(b"ngb")
    return SeededInputs(staged=(csv_path,), queued=(ngb_path,))


def _assert_psa(dest_dir: Path) -> None:
    record_dir = _record_dir(dest_dir, "ipat", "usr", "PSA", "psa1")
    assert record_dir.exists()
    _assert_single_suffix(record_dir, ".csv")
    _assert_single_suffix(record_dir, ".zip")


def _seed_kinexus(watch_dir: Path) -> SeededInputs:
    csv_path = watch_dir / "usr-ipat-rhe1.csv"
    rdf_path = watch_dir / "usr-ipat-rhe1.rdf"
    csv_path.write_text(
        "KInexus NETZSCH viscosity data\nG' G\"",
        encoding="utf-8",
    )
    rdf_path.write_bytes(b"rdf")
    return SeededInputs(staged=(csv_path,), queued=(rdf_path,))


def _assert_kinexus(dest_dir: Path) -> None:
    record_dir = _record_dir(dest_dir, "ipat", "usr", "RHE", "rhe1")
    assert record_dir.exists()
    _assert_single_suffix(record_dir, ".csv")
    _assert_single_suffix(record_dir, ".zip")


def _seed_eirich_el1(watch_dir: Path) -> SeededInputs:
    path = watch_dir / "Eirich_EL1_TrendFile_20250924_095653.txt"
    path.write_text("eirich el1", encoding="utf-8")
    return SeededInputs(staged=(), queued=(path,))


def _assert_eirich_el1(dest_dir: Path) -> None:
    record_dir = _record_dir(dest_dir, "ipat", "mus", "RMX_01", "el1")
    assert record_dir.exists()
    _assert_single_suffix(record_dir, ".txt")


def _seed_eirich_r01(watch_dir: Path) -> SeededInputs:
    path = watch_dir / "Eirich_R01_TrendFile_20250731_103330.txt"
    path.write_text("eirich r01", encoding="utf-8")
    return SeededInputs(staged=(), queued=(path,))


def _assert_eirich_r01(dest_dir: Path) -> None:
    record_dir = _record_dir(dest_dir, "ipat", "mus", "RMX_02", "r01")
    assert record_dir.exists()
    _assert_single_suffix(record_dir, ".txt")


def _seed_sem(watch_dir: Path) -> SeededInputs:
    path = watch_dir / "usr-ipat-sem1.tif"
    path.write_bytes(b"tif")
    return SeededInputs(staged=(), queued=(path,))


def _assert_sem(dest_dir: Path) -> None:
    record_dir = _record_dir(dest_dir, "ipat", "usr", "SEM", "sem")
    assert record_dir.exists()
    _assert_single_suffix(record_dir, ".tif")


def _seed_utm(watch_dir: Path) -> SeededInputs:
    zs2 = watch_dir / "usr-ipat-utm1.zs2"
    xlsx = watch_dir / "usr-ipat-utm1.xlsx"
    zs2.write_bytes(b"zs2")
    xlsx.write_bytes(b"xlsx")
    return SeededInputs(staged=(zs2,), queued=(xlsx,))


def _assert_utm(dest_dir: Path) -> None:
    record_dir = _record_dir(dest_dir, "ipat", "usr", "UTM", "utm1")
    assert record_dir.exists()
    _assert_min_suffix(record_dir, ".zs2", 1)
    _assert_min_suffix(record_dir, ".xlsx", 1)


DEVICE_SPECS = (
    DeviceSpec(
        name="extr_haake",
        seed_inputs=_seed_extr_haake,
        assert_outputs=_assert_extr_haake,
    ),
    DeviceSpec(
        name="erm_hioki",
        seed_inputs=_seed_hioki,
        assert_outputs=_assert_hioki,
    ),
    DeviceSpec(
        name="dsv_horiba",
        seed_inputs=_seed_dsv,
        assert_outputs=_assert_dsv,
    ),
    DeviceSpec(
        name="psa_horiba",
        seed_inputs=_seed_psa,
        assert_outputs=_assert_psa,
    ),
    DeviceSpec(
        name="rhe_kinexus",
        seed_inputs=_seed_kinexus,
        assert_outputs=_assert_kinexus,
    ),
    DeviceSpec(
        name="rmx_eirich_el1",
        seed_inputs=_seed_eirich_el1,
        assert_outputs=_assert_eirich_el1,
        rename_inputs=({"name": "mus", "institute": "ipat", "sample_ID": "el1"},),
    ),
    DeviceSpec(
        name="rmx_eirich_r01",
        seed_inputs=_seed_eirich_r01,
        assert_outputs=_assert_eirich_r01,
        rename_inputs=({"name": "mus", "institute": "ipat", "sample_ID": "r01"},),
    ),
    DeviceSpec(
        name="sem_phenomxl2",
        seed_inputs=_seed_sem,
        assert_outputs=_assert_sem,
    ),
    DeviceSpec(
        name="utm_zwick",
        seed_inputs=_seed_utm,
        assert_outputs=_assert_utm,
    ),
)


@pytest.mark.parametrize("spec", DEVICE_SPECS, ids=lambda spec: spec.name)
def test_device_integrations_uber_pc(tmp_path, monkeypatch, spec: DeviceSpec) -> None:
    app, ui, sync, paths = _setup_app(tmp_path, monkeypatch)
    try:
        ui.rename_inputs = list(spec.rename_inputs)
        seeded = spec.seed_inputs(paths.watch_dir)
        for path in seeded.staged:
            app.file_processing.process_item(str(path))
        for path in seeded.queued:
            app.event_queue.put(str(path))
        drain_scheduled_tasks(ui, max_steps=200)
        spec.assert_outputs(paths.dest_dir)
        assert sync.synced_records
        assert not ui.errors
    finally:
        app.on_closing()
        reset_service()


def test_multi_device_routing_smoke(tmp_path, monkeypatch) -> None:
    app, ui, sync, paths = _setup_app(tmp_path, monkeypatch)
    try:
        multi_specs = (
            DEVICE_SPECS[5],  # rmx_eirich_el1
            DEVICE_SPECS[3],  # psa_horiba
            DEVICE_SPECS[4],  # rhe_kinexus
            DEVICE_SPECS[7],  # sem_phenomxl2
            DEVICE_SPECS[0],  # extr_haake
            DEVICE_SPECS[8],  # utm_zwick
        )
        ui.rename_inputs = [item for spec in multi_specs for item in spec.rename_inputs]

        staged: list[Path] = []
        queued: list[Path] = []
        for spec in multi_specs:
            seeded = spec.seed_inputs(paths.watch_dir)
            staged.extend(seeded.staged)
            queued.extend(seeded.queued)

        for path in staged:
            app.file_processing.process_item(str(path))
        for path in queued:
            app.event_queue.put(str(path))

        drain_scheduled_tasks(ui, max_steps=400)
        for spec in multi_specs:
            spec.assert_outputs(paths.dest_dir)

        assert sync.synced_records
        assert not ui.errors
    finally:
        app.on_closing()
        reset_service()
