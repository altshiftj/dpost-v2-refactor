# Report: V2 RuntimeHost Refactor

## Scope
- Goal:
  - promote runtime lifecycle ownership into a first-class `RuntimeHost`
  - stop treating the app object as the canonical runtime handle
  - keep the already-green shutdown behavior while improving the architecture
    before frozen/bootstrap and PyInstaller work

## Changes
- Added `RuntimeHost` in:
  - `src/dpost_v2/application/runtime/runtime_host.py`
- Refactored composition so it now constructs:
  - `DPostApp` as the runtime application object
  - `RuntimeHost` as the canonical lifecycle owner
- Updated `CompositionBundle` so the canonical runtime surface is:
  - `runtime_handle`
- Kept `CompositionBundle.app` as a diagnostic/testing convenience only.
- Updated bootstrap so successful launch now consumes:
  - `composition.runtime_handle`
  instead of:
  - `composition.app`
- Removed the app-owned shutdown seam from `DPostApp`.

## Tests Added First
- `tests/dpost_v2/application/runtime/test_runtime_host.py`
  - host delegates `run()` to the app
  - host shutdown is idempotent
- `tests/dpost_v2/runtime/test_composition.py`
  - default composed runtime surface is a `RuntimeHost`
  - host shutdown shares the bundle shutdown hook
- `tests/dpost_v2/application/startup/test_bootstrap.py`
  - bootstrap launches the composed runtime handle, not the app
- `tests/dpost_v2/smoke/test_bootstrap_harness_smoke.py`
  - smoke harness sees the runtime handle surface from bootstrap

## Validation
- `python -m pytest -q tests/dpost_v2/application/runtime/test_runtime_host.py tests/dpost_v2/runtime/test_composition.py -k "runtime_host or default_factory_returns_runtime_app_surface or runtime_handle_shutdown_uses_bundle_shutdown_hook or shutdown_hook_is_idempotent"`
  - passed
- `python -m pytest -q tests/dpost_v2/application/startup/test_bootstrap.py tests/dpost_v2/smoke/test_bootstrap_harness_smoke.py`
  - passed
- `python -m pytest -q tests/dpost_v2/application/runtime tests/dpost_v2/runtime tests/dpost_v2/test___main__.py`
  - passed

## Outcome
- `RuntimeHost` is now the canonical lifecycle owner for V2 runtime execution.
- `DPostApp` is no longer the final owner of adapter cleanup semantics.
- Bootstrap and CLI continue to consume a generic runtime handle contract, but
  that contract now resolves cleanly to the host rather than the app.
- Frozen/bootstrap and PyInstaller work can now proceed on the cleaner runtime
  lifecycle boundary.

## Remaining Follow-On
- frozen bootstrap/path contract
- V2 PyInstaller build baseline
- manual workstation probe for continuous resident execution and clean exit
