# 20260305 V2 PC/Device Runtime Wiring Readiness Report

## Title
- V2 manual bring-up readiness before runtime wiring

## Date
- 2026-03-05

## Context
- Manual validation was run to confirm current V2 startup behavior, plugin discovery, profile activation, and concrete plugin contract execution.
- Objective of this report is to document readiness and remaining gap before true file-processing runtime behavior.

## Findings
- V2 CLI startup path is stable for `dpost --mode v2` with `--headless` and `--dry-run`.
- Plugin discovery and profile activation are working using `discover_from_namespaces()` and `PluginHost.activate_profile(...)`.
- Concrete plugin contract calls work for both a device plugin (`psa_horiba`) and PC plugin (`horiba_blb`).
- Architecture intent is clarified: PC plugin is workstation policy/scope (can own multiple device plugins), while sync transport is handled by sync backend adapters.
- Core gap remains: runtime composition still defaults to `_NoopIngestionEngine`, so CLI startup does not yet execute real ingestion processing over incoming files.
- Bootstrap/entrypoint flow returns success after startup bootstrap, but does not currently force an end-to-end runtime ingestion pass in normal headless launch.

## Evidence
- Code evidence:
  - [composition.py](d:/Repos/d-post/src/dpost_v2/runtime/composition.py:240) injects `_NoopIngestionEngine()`.
  - [composition.py](d:/Repos/d-post/src/dpost_v2/runtime/composition.py:476) defines `_NoopIngestionEngine`.
  - [bootstrap.py](d:/Repos/d-post/src/dpost_v2/application/startup/bootstrap.py:92) defaults `launch_runtime` to returning the app handle.
  - [bootstrap.py](d:/Repos/d-post/src/dpost_v2/application/startup/bootstrap.py:224) assigns `runtime_handle = launch_runtime(...)`.
  - [__main__.py](d:/Repos/d-post/src/dpost_v2/__main__.py:55) calls bootstrap `run(...)`.
  - [__main__.py](d:/Repos/d-post/src/dpost_v2/__main__.py:63) returns success based on bootstrap result.
- Manual command evidence (executed 2026-03-05):
  - `python -m dpost --mode v2 --profile prod --headless --dry-run` -> startup succeeded.
  - `python -m dpost --mode v2 --profile prod --headless` -> startup succeeded.
  - Discovery output listed expected device and PC plugins.
  - Processor smoke for `psa_horiba` returned valid result payload.
  - PC plugin shaping smoke for `horiba_blb` returned valid workstation payload data for downstream sync transport.
  - `python -m pytest -q tests/dpost_v2/plugins/test_discovery.py tests/dpost_v2/plugins/test_device_integration.py tests/dpost_v2/runtime` -> passed.

## Risks
- False confidence risk: startup success can be misread as full ingestion success while runtime is still noop by default.
- Integration risk: wiring real ingestion into runtime may surface contract mismatches between startup context, ingestion state, and plugin selection.
- Operational risk: without deterministic headless event source behavior, manual validation may remain ambiguous.

## Open Questions
- Should headless non-dry-run execute one deterministic batch then exit, or run watch-loop continuously?
  - Answer: define deterministic single-pass mode first for repeatable manual validation; add continuous mode after baseline is stable.
- Should plugin pair selection be explicit via config, profile-driven, or both?
  - Answer: keep profile-driven default with PC-scoped device ownership, then add explicit override controls only if required by operations.
- Should runtime wiring ship as one slice or multiple guarded slices?
  - Answer: multiple TDD slices with green checkpoints is safer and easier to debug.
