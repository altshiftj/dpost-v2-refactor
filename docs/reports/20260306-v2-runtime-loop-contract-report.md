# Report: V2 Runtime Loop Contract

## Scope
- Goal:
  - introduce explicit one-shot vs continuous headless runtime behavior
  - keep current one-shot semantics intact
  - prove continuous mode can process a file that arrives after startup

## Changes
- Added runtime loop policy to startup settings:
  - `runtime.loop_mode`
  - `runtime.poll_interval_seconds`
  - `runtime.idle_timeout_seconds`
  - `runtime.max_runtime_seconds`
- Refactored `DPostApp` to support:
  - one-shot batch execution
  - continuous polling cycles
  - injected idle wait via clock `sleep()` or `time.sleep`
  - duplicate suppression across poll cycles
- Updated headless composition so directory discovery can be re-run each cycle
  in continuous mode while still preserving explicit UI-provided event sources.

## Tests Added First
- `tests/dpost_v2/application/runtime/test_dpost_app.py`
  - one-shot consumes one polled batch
  - continuous mode processes late-arriving event
  - continuous mode soft-times-out while idle
  - duplicate event ids are skipped across poll cycles
- `tests/dpost_v2/application/startup/test_settings_schema.py`
  - runtime loop policy block is accepted
- `tests/dpost_v2/application/startup/test_settings.py`
  - runtime loop settings normalize correctly
  - negative poll interval is rejected
- `tests/dpost_v2/application/startup/test_settings_service.py`
  - config-file runtime loop policy is loaded
- `tests/dpost_v2/runtime/test_composition.py`
  - continuous headless mode processes a file created after startup

## Validation
- `python -m pytest -q tests/dpost_v2/application/runtime/test_dpost_app.py`
  - passed
- `python -m pytest -q tests/dpost_v2/application/startup/test_settings_schema.py tests/dpost_v2/application/startup/test_settings.py tests/dpost_v2/application/startup/test_settings_service.py`
  - passed
- `python -m pytest -q tests/dpost_v2/runtime/test_composition.py -k "default_app_consumes_ui_event_source or continuous_headless_processes_file_arriving_after_startup or headless_fallback_event_source_scans_watch_dir"`
  - passed
- `python -m ruff check src/dpost_v2 tests/dpost_v2`
  - passed
- `python -m pytest -q tests/dpost_v2`
  - `437 passed`

## Outcome
- The resident runtime seam now exists in the canonical V2 path.
- Continuous headless mode is source-configurable and can process files that
  arrive after startup.
- The previous one-shot behavior is still green.

## Remaining Follow-On
- explicit clean shutdown verification for adapters after continuous runs
- frozen bootstrap/path contract
- V2 PyInstaller build baseline
