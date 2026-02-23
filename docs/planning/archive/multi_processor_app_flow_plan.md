# Multi-Processor App Flow Integration Test Plan

## Goals
- [x] Exercise full app flow with multiple processors (Eirich EL1 + Eirich R01 + UTM Zwick).
- [x] Validate device resolution via probe logic when multiple devices match.
- [x] Confirm record routing, file moves, and session sync behavior across devices.
Notes:
- Covered in `tests/integration/test_multi_processor_app_flow.py`.

## Test Scope
- [x] Use `DeviceWatchdogApp` + real `FileProcessManager` with real processors.
- [x] Initialize config with multiple device configs and sandboxed test paths.
- [x] Drive event queue + scheduler to simulate app loop behavior.
Notes:
- Uses a sandboxed temp tree plus the real app + processing manager.

## Setup Tasks
- [x] Create a test-specific config builder that registers EL1, R01, and UTM configs.
- [x] Override watcher timings for faster stability checks in tests.
- [x] Ensure `HeadlessUI` rename inputs cover Eirich filename validation paths.
- [x] Ensure plugin loading is not required (use direct `init_config` with configs).
Notes:
- The fixture builds configs directly and monkeypatches stability waiting.
- Plugins are registered explicitly for the test without entrypoint discovery.

## Core Scenarios
- [x] Mixed intake: enqueue EL1 `.txt`, R01 `.txt`, and UTM `.zs2/.txt/.csv`.
- [x] Verify Eirich files route to the correct device based on filename probe.
- [x] Verify UTM series is staged on `.zs2/.txt` and finalized on `.csv`.
- [x] Verify all files are moved out of `watch_dir` and into correct record dirs.
Notes:
- Scenario is exercised end-to-end via event queue + task drain.

## Assertions
- [x] Record folders created under expected device abbreviations (`RMX_01`, `RMX_02`, `UTM`).
- [x] Eirich outputs use unique filenames and are marked processed.
- [x] UTM outputs include unique `.zs2`, `.csv`, and snapshot `.txt` files.
- [x] No unexpected rejections; rejected queue remains empty.
- [x] Optional: `DummySyncManager` received sync calls if immediate sync is enabled.
Notes:
- Assertions verify directories, file counts, and sync activity.

## Follow-ups
- [x] Add negative case for invalid Eirich filename (rename flow to manual bucket).
- [x] Consider parameterizing for additional devices later (sem/psa/etc.).
Notes:
- Added a rename-cancel test that confirms items move to the rename folder.
- Refactored the integration test to use device spec tables for easier extension.
