# Device Integration Test Plan

## Summary

Yes, the test idea makes sense: a parameterized integration test can validate end-to-end flows (drop -> naming -> sync) across device plugins. In practice, it should be data-driven and split into two layers to stay reliable and fast:

- Plugin discovery smoke: ensure each device plugin can be loaded and its config constructed.
- Per-device processing smoke: run a minimal, device-specific happy path using sandboxed paths.

Some devices need multi-file sequences or content markers (PSA, Kinexus, DSV, UTM, SEM), so each device needs a small, purpose-built input builder.

## Goals

- Instantiate `DeviceWatchdogApp` with sandboxed paths for each device.
- Validate plugins are discoverable and loadable.
- Process the minimal expected file types per device and confirm:
  - Record folder naming and file naming.
  - Sync manager invoked (or records marked uploaded) after processing.

## Non-goals

- Full vendor file fidelity or large real datasets.
- Exhaustive probe logic across multiple devices in a single test.
- Stability timing or file watcher OS behavior (use stubs).

## Proposed Test Shape

Create `tests/integration/test_device_integrations.py` with a spec table and helper functions. Each spec owns its input creation and assertions.

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ipat_watchdog.core.config import init_config, reset_service
from ipat_watchdog.core.processing.stability_tracker import FileStabilityTracker, StabilityOutcome
from ipat_watchdog.core.app.device_watchdog_app import DeviceWatchdogApp
from tests.helpers.fake_observer import FakeObserver
from tests.helpers.fake_sync import DummySyncManager
from tests.helpers.fake_ui import HeadlessUI
from tests.helpers.task_runner import drain_scheduled_tasks


@dataclass(frozen=True)
class DeviceSpec:
    name: str
    build_config: Callable[[], object]
    seed_inputs: Callable[[Path], list[Path]]
    assert_outputs: Callable[[Path], None]
    rename_inputs: list[dict[str, str]] = field(default_factory=list)


def _stable_immediately(self):
    return StabilityOutcome(path=self.file_path, stable=True)


def _build_app(tmp_path: Path, device_config):
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
    service = init_config(pc_config, [device_config])
    init_dirs()

    ui = HeadlessUI()
    ui.rename_inputs = list(getattr(device_config, "rename_inputs", []))
    sync = DummySyncManager(ui)
    app = DeviceWatchdogApp(ui=ui, sync_manager=sync, config_service=service)
    return app, ui, sync, overrides["watch_dir"], overrides["dest_dir"]


@pytest.mark.parametrize("spec", DEVICE_SPECS, ids=lambda s: s.name)
def test_device_processing_smoke(tmp_path, monkeypatch, spec):
    monkeypatch.setattr(FileStabilityTracker, "wait", _stable_immediately)
    monkeypatch.setattr("ipat_watchdog.core.app.device_watchdog_app.Observer", lambda: FakeObserver())

    device_config = spec.build_config()
    app, ui, sync, watch_dir, dest_dir = _build_app(tmp_path, device_config)
    ui.rename_inputs = list(spec.rename_inputs)
    app.initialize()
    try:
        for path in spec.seed_inputs(watch_dir):
            app.event_queue.put(str(path))
        drain_scheduled_tasks(ui)
        spec.assert_outputs(dest_dir)
        assert sync.synced_records
    finally:
        app.on_closing()
        reset_service()
```

Notes:
- Patch `FileStabilityTracker.wait` to avoid timing delays.
- Use the real `DeviceWatchdogApp` to satisfy "app instantiated" and event queue flow.
- Use a single device per test to avoid probe ambiguity; keep probe coverage in separate tests.

## Device Matrix (Minimal Inputs)

Below are minimal viable inputs that exercise the pipeline and naming. Each entry assumes filenames already match the `<user>-<institute>-<sample>` prefix to avoid interactive rename, unless noted.

- `extr_haake`
  - Input: `usr-ipat-extr1.xlsx`
  - Expected: `Data/IPAT/USR/EXTR-extr1/EXTR-extr1-01.xlsx`
- `erm_hioki`
  - Input: `usr-ipat-hioki_20250101120000.csv` (measurement)
  - Optional: `CC_usr-ipat-hioki.csv`, `usr-ipat-hioki.csv` to validate forced paths
  - Expected: `ERM-hioki-01.csv` plus `ERM-hioki-cc.csv` and `ERM-hioki-results.csv`
- `dsv_horiba`
  - Input: one batch key with raw + export
    - Raw: `usr-ipat-dsv1.wdb`, `usr-ipat-dsv1.wdk`, `usr-ipat-dsv1.wdp`
    - Export: confirm expected extension (.txt vs .xls)
  - Expected: `<prefix>_raw_data.zip` plus exported file(s)
  - Open question: `settings.py` exports `.xls` but processor expects `.txt`.
- `psa_horiba`
  - Input sequence: `usr-ipat-psa1.csv` containing header `Probenname;usr-ipat-psa1`, then `usr-ipat-psa1.ngb`
  - Expected: `PSA-psa1-01.csv` and `PSA-psa1-01.zip`
- `rhe_kinexus`
  - Input sequence: `usr-ipat-rhe1.csv` then `usr-ipat-rhe1.rdf`
  - Expected: `RHE-rhe1-01.csv` and `RHE-rhe1-01.zip`
- `rmx_eirich_el1`
  - Input: `Eirich_EL1_TrendFile_20250924_095653.txt`
  - Rename input required: `{name: "mus", institute: "ipat", sample_ID: "el1"}`
  - Expected: `Data/IPAT/MUS/RMX_01-el1/*.txt`
- `rmx_eirich_r01`
  - Input: `Eirich_R01_TrendFile_20250731_103330.txt`
  - Rename input required: `{name: "mus", institute: "ipat", sample_ID: "r01"}`
  - Expected: `Data/IPAT/MUS/RMX_02-r01/*.txt`
- `sem_phenomxl2`
  - Input: `usr-ipat-sem1.tif`
  - Expected: `SEM-sem1-01.tif`
  - Optional extended case: an `.elid` directory with `export/` and `.odt` files
- `utm_zwick`
  - Input sequence: `usr-ipat-utm1.zs2`, `usr-ipat-utm1-01.txt`, `usr-ipat-utm1-02.txt`, then `usr-ipat-utm1.csv`
  - Expected: `UTM-utm1-01.zs2`, `UTM-utm1_results-01.csv`, `UTM-utm1_tests-01.txt` (and additional snapshots)

## Plugin Discovery Smoke Test

Add a small test that asserts all device plugins can be loaded:

- Use `PluginLoader(load_builtins=True)` and assert `available_device_plugins()` contains the expected device ids.
- For each device id, call `load_device()` and assert `get_config()` returns a `DeviceConfig`.

This keeps discovery failures separate from file-processing failures.

## Risks / Watchouts

- Probes and selectors are bypassed if only one device is configured; use separate probe tests if needed.
- Some processors keep files in place (e.g., Hioki aggregate copies). Choose inputs that trigger file moves when testing "drop -> move".
- DSV exported extension mismatch should be resolved before asserting outputs.
- PSA and Kinexus staging relies on order and minimal metadata; keep inputs deterministic.

## Suggested Next Steps

1. Decide whether the integration test should target one device at a time or use PC configs with multiple devices.
2. Confirm DSV export extension and adjust the spec accordingly.
3. Implement `tests/integration/test_device_integrations.py` following the spec table.
