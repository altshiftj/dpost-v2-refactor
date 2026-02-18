# Coverage Findings Report

## Critical Gaps (0–50%)
- `src/ipat_watchdog/__main__.py`: 0% coverage (missing lines include 3, 34); the CLI entrypoint is untested.
- `src/ipat_watchdog/pc_plugins/haake_blb/plugin.py`: 0% coverage (missing line 3); Haake PC plugin registration is untested.
- `src/ipat_watchdog/pc_plugins/haake_blb/settings.py`: 0% coverage (missing line 3); Haake PC plugin settings are untested.
- `src/ipat_watchdog/observability.py`: 32% coverage (missing lines include 15, 85); observability server wiring and routes are untested.
- `src/ipat_watchdog/core/processing/error_handling.py`: 42% coverage (missing lines include 18, 61); exception handling paths and safe-move fallbacks are untested.
- `src/ipat_watchdog/core/processing/modified_event_gate.py`: 48% coverage (missing lines include 37, 76); modified-event gating logic is untested.

## Core Pipeline Gaps (50–70%)
- `src/ipat_watchdog/core/app/bootstrap.py`: 59% coverage (missing lines include 27, 211); startup env/override branches are untested.
- `src/ipat_watchdog/core/processing/device_resolver.py`: 67% coverage (missing lines include 37, 210); probe-based resolution branches are untested.
- `src/ipat_watchdog/core/processing/stability_tracker.py`: 68% coverage (missing lines include 55, 180); stability/rejection paths are untested.
- `src/ipat_watchdog/core/storage/filesystem_utils.py`: 64% coverage (missing lines include 40, 420); naming, move, and error branches are untested.
- `src/ipat_watchdog/core/ui/ui_tkinter.py`: 53% coverage (missing lines include 59, 215); GUI paths beyond headless adapters are untested.

## Device Processor Gaps
- `src/ipat_watchdog/device_plugins/psa_horiba/file_processor.py`: 72% coverage (missing lines include 130, 589); staging/purge/fallback branches are untested.
- `src/ipat_watchdog/device_plugins/rhe_kinexus/file_processor.py`: 63% coverage (missing lines include 32, 446); staging/reconstruction branches are untested.
- `src/ipat_watchdog/device_plugins/dsv_horiba/file_processor.py`: 79% coverage (missing lines include 73, 190); batch readiness/purge branches are untested.
