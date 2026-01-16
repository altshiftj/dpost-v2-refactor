# Coverage Improvement Checklist

Goal: raise overall coverage by targeting the largest uncovered areas first.

## Priority 1: 0–50% Coverage
- [x] Add tests for the CLI entrypoint path in `src/ipat_watchdog/__main__.py`.
  - Notes: exercise main dispatch and error/usage behavior.
- [x] Add tests for Haake PC plugin registration and settings in `src/ipat_watchdog/pc_plugins/haake_blb/plugin.py` and `src/ipat_watchdog/pc_plugins/haake_blb/settings.py`.
  - Notes: verify plugin loads and config matches expected defaults.
- [x] Add tests for `src/ipat_watchdog/observability.py` HTTP routes.
  - Notes: cover `/health` and `/logs` paths plus failure handling.
- [x] Add tests for `src/ipat_watchdog/core/processing/error_handling.py`.
  - Notes: cover exception moves and fallbacks on missing paths.
- [x] Add tests for `src/ipat_watchdog/core/processing/modified_event_gate.py`.
  - Notes: verify gating rules and device override handling.

## Priority 2: Core Pipeline (50–70% Coverage)
- [x] Add tests for `src/ipat_watchdog/core/app/bootstrap.py` env/override branches.
  - Notes: cover env var overrides and missing configuration paths.
- [x] Add tests for `src/ipat_watchdog/core/processing/device_resolver.py` probe-driven resolution.
  - Notes: exercise match/mismatch/unknown probe outcomes.
- [x] Add tests for `src/ipat_watchdog/core/processing/stability_tracker.py` edge cases.
  - Notes: include rejected outcomes and timeout behavior.
- [x] Add tests for `src/ipat_watchdog/core/storage/filesystem_utils.py` error paths.
  - Notes: cover rename collisions and exceptional moves.
- [x] Add tests for `src/ipat_watchdog/core/ui/ui_tkinter.py` non-UI logic via adapters/mocks.
  - Notes: keep UI dependencies mocked; avoid real GUI.

## Priority 3: Device Processor Gaps
- [x] Add tests for PSA Horiba staging/purge fallbacks in `src/ipat_watchdog/device_plugins/psa_horiba/file_processor.py`.
  - Notes: cover stale purge paths and stage reconstruction.
- [x] Add tests for Kinexus staging/reconstruction in `src/ipat_watchdog/device_plugins/rhe_kinexus/file_processor.py`.
  - Notes: cover `_reconstruct_batch_from_stage` fallback logic.
- [x] Add tests for DSV Horiba batch readiness/purge in `src/ipat_watchdog/device_plugins/dsv_horiba/file_processor.py`.
  - Notes: cover readiness transitions and orphan purge paths.
