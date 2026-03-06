# Report: V2 Shutdown and Lifecycle Contract

## Scope
- Goal:
  - make runtime shutdown explicit and deterministic for non-dry-run execution
  - keep adapter cleanup idempotent
  - preserve existing success/failure terminal semantics while adding clean
    lifecycle handling

## Changes
- Added an idempotent `shutdown()` method to `DPostApp`.
- Refactored runtime composition to build one shared shutdown hook and expose it
  through both:
  - the default `DPostApp`
  - `CompositionBundle.shutdown_all`
- Updated the V2 CLI entrypoint so `_execute_runtime()` always invokes runtime
  shutdown in a `finally` path after calling `run()`.
- Kept shutdown optional on runtime handles for compatibility. When absent, the
  runtime shutdown step becomes a no-op.
- Added deterministic shutdown error handling:
  - runtime shutdown failure returns exit code `1`
  - a prior runtime failure still owns the exit path

## Tests Added First
- `tests/dpost_v2/application/runtime/test_dpost_app.py`
  - shutdown hook is idempotent
- `tests/dpost_v2/runtime/test_composition.py`
  - default composed app shares the bundle shutdown hook
- `tests/dpost_v2/test___main__.py`
  - non-dry-run success calls runtime shutdown
  - runtime exception still triggers shutdown
  - `KeyboardInterrupt` still triggers shutdown
  - shutdown failure maps to exit code `1`

## Validation
- `python -m pytest -q tests/dpost_v2/application/runtime/test_dpost_app.py tests/dpost_v2/runtime/test_composition.py tests/dpost_v2/test___main__.py`
  - passed
- `python -m ruff check src/dpost_v2 tests/dpost_v2`
  - passed
- `python -m pytest -q tests/dpost_v2`
  - `441 passed`

## Outcome
- The canonical V2 runtime now has an explicit lifecycle seam:
  - `run()`
  - `shutdown()`
- Adapter cleanup is idempotent at both the app and composition-bundle levels.
- Non-dry-run CLI execution now cleans up deterministically after:
  - normal completion
  - runtime failure
  - interruption

## Remaining Follow-On
- frozen bootstrap/path contract
- V2 PyInstaller build baseline
- manual workstation probe for continuous resident execution and clean exit
