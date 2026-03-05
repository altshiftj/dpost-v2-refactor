# 20260305 V2 Standalone Runtime Ceiling Report

## Title
- V2 standalone execution ceiling re-validation (headless)

## Date
- 2026-03-05

## Objective
- Re-establish how far `dpost` V2 runs in standalone mode today before additional runtime wiring and plugin migration work.

## Scope
- CLI startup and runtime execution path from `python -m dpost`.
- Headless deterministic processing pass over real files in isolated temp folders.
- Startup dependency guardrails (`config` source handling and `kadi` token requirement).
- No code changes to runtime behavior in this probe.

## Environment
- Repo: `D:\Repos\dpost-v2-refactor`
- Branch: `main`
- Python: `3.12.7`
- Probe date/time (local): 2026-03-05

## Gate Matrix (Pass/Fail)

| Gate | Description | Result | Evidence |
|---|---|---|---|
| G1 | Raw standalone importability (`python -m dpost` from repo shell) | FAIL | `No module named dpost` until `PYTHONPATH=src` is set |
| G2 | CLI surface availability (`--help`) with import path prepared | PASS | Usage output rendered with `--mode {v2}` |
| G3 | Dry-run startup contract | PASS | `--dry-run` exits `0` and reports startup success |
| G4 | Non-dry-run runtime contract | PASS | Non-dry-run exits `0` and reports startup success |
| G5 | Real filesystem side effects in headless standalone run | FAIL | Files remain in `incoming/`; `processed/` remains empty |
| G6 | Concrete plugin selection during runtime processing | FAIL | Probe resolved runtime processor to `plugin_id=default_device` |
| G7 | Missing config path settings guardrail | PASS | Missing config file fails at `settings` stage with exit `1` |
| G8 | `kadi` dependency token guardrail | PASS | No token -> fail (`1`); token present -> success (`0`) |

## Command Transcript

### 1) Preflight and CLI discovery
- Command: `git status --short --branch`
  - Result: `## main...origin/main` with untracked user-intent paths (`docs/planning/20260305-v2-three-plugin-phased-migration-rpc.md`, `src/ipat_watchdog/`).
- Command: `python --version`
  - Result: `Python 3.12.7`
- Command: `python -m dpost --help`
  - Result: failed with `No module named dpost`
- Command: `$env:PYTHONPATH='src'; python -m dpost --help`
  - Result: CLI usage printed successfully.

### 2) Startup/runtime contract with import path prepared
- Command: `$env:PYTHONPATH='src'; python -m dpost --mode v2 --profile prod --headless --dry-run`
  - Result: `dpost startup succeeded (mode=v2, profile=prod).` (exit `0`)
- Command: `$env:PYTHONPATH='src'; python -m dpost --mode v2 --profile prod --headless`
  - Result: `dpost startup succeeded (mode=v2, profile=prod).` (exit `0`)

### 3) Isolated standalone headless file-processing probe
- Probe root created:
  - `C:\Users\fitz\AppData\Local\Temp\dpost_v2_standalone_probe_20260305-170101`
- Probe setup:
  - `incoming/`: `sample_psa.ngb`, `sample_sem.tif`, `sample_utm.xlsx`
  - `processed/`: empty at start
  - `tmp/`: created
- Command:
  - `PYTHONPATH=<repo>\\src; python -m dpost --mode v2 --profile prod --headless` (run from probe root)
- Result:
  - CLI exit: `0`
  - `incoming` after run: `sample_psa.ngb`, `sample_sem.tif`, `sample_utm.xlsx`
  - `processed` after run: empty

### 4) Internal composition/runtime ceiling probe
- Command: inline Python probe (with `PYTHONPATH=src`) composing runtime via startup services and running one event + full run.
- Observed:
  - `bundle_plugin_binding_type = dict`
  - `bundle_storage_binding_type = dict`
  - `bundle_filesystem_binding_type = dict`
  - `bundle_sync_binding_type = dict`
  - `probe_plugin_id = default_device`
  - `probe_processor_key = default_device`
  - `run_processed_count = 3`
  - `run_failed_count = 0`
  - `run_terminal_reason = end_of_stream`
  - Files still remained in `incoming/`; no files appeared in `processed/`.

### 5) Guardrail probes
- Missing config path:
  - Command: `$env:PYTHONPATH='src'; python -m dpost --mode v2 --profile prod --headless --config C:\\this\\path\\does\\not\\exist.json`
  - Result: exit `1`; startup failed at `settings` with `Config file not found`.
- `kadi` backend token requirement:
  - Config file used:
    - `C:\Users\fitz\AppData\Local\Temp\dpost_v2_kadi_probe_20260305-170157\config.json`
    - Payload: `{"sync":{"backend":"kadi"}}`
  - Without `KADI_API_TOKEN`:
    - Result: exit `1`; failure at `dependencies` with token requirement.
  - With `KADI_API_TOKEN=probe-token`:
    - Result: exit `0`; startup succeeded.

## Ceiling Summary
- Current standalone V2 capability:
  - Startup + runtime loop orchestration works.
  - Headless deterministic event traversal works.
  - Guardrails for settings and sync dependency inputs work.
- Current standalone V2 limitation:
  - Default path does not yet perform real adapter-backed file movement/persistence for real artifacts.
  - Runtime resolution still falls back to `default_device` in the observed default composition path.

## Conclusion
- Standalone runtime is operational at orchestration level but not yet at concrete ingestion-effect level for target device plugins.
- This confirms the current migration boundary before plugin-behavior and runtime-wiring hardening slices.
