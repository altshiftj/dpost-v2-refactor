# Checklist: V2 Stabilization Runtime Resilience

## Why this matters
- Repeated V2 launches and failure paths must remain deterministic so operators and CI receive stable behavior.
- Startup/shutdown hardening reduces flaky cleanup behavior when partial startup fails.
- Structured startup events must be consistent for observability and incident triage.

## Manual Check
- [x] Add failing tests first for startup/shutdown idempotency, failure payload structure, and deterministic exit-code mapping.
- [x] Implement minimal runtime/startup changes to satisfy tests without introducing retired runtime modes.
- [x] Verify dry-run and non-dry-run launch-failure cleanup order is identical.
- [x] Run lane-targeted tests and full V2 checks.
- [x] Commit lane slice checkpoint from lane worktree.

## Behavior Slice: Deterministic Exit Code Mapping
- Why this matters: parser-triggered `SystemExit` values must not leak non-deterministic conversion errors into CLI behavior.

### Checklist
- [x] Added `tests/dpost_v2/test___main__.py::test_main_handles_non_integer_system_exit_code_deterministically`.
- [x] Updated `src/dpost_v2/__main__.py` to coerce `SystemExit.code` via `_coerce_system_exit_code(...)`.
- [x] Confirmed non-integer `SystemExit.code` maps to exit code `1`.

### Completion Notes
- How it was done: `main(...)` now uses `_coerce_system_exit_code` to return `0` for `None`, integer values directly, and fallback `1` for non-numeric values.

---

## Behavior Slice: Idempotent Startup/Shutdown Cleanup
- Why this matters: repeated shutdown invocation and duplicate cleanup hooks should not produce duplicate side effects or unstable failures.

### Checklist
- [x] Added `tests/dpost_v2/runtime/test_composition.py::test_composition_shutdown_hook_is_idempotent`.
- [x] Updated `src/dpost_v2/runtime/composition.py` shutdown hook builder to run once and ignore duplicate bound methods.
- [x] Updated `src/dpost_v2/application/startup/bootstrap.py` cleanup runner to clear hook list and de-duplicate hooks before execution.
- [x] Added `tests/dpost_v2/application/startup/test_bootstrap.py::test_bootstrap_cleanup_order_is_stable_for_dry_run_and_non_dry_run`.

### Completion Notes
- How it was done: composition shutdown is now one-shot (`has_run` guard) and startup cleanup consumes a snapshot of hooks, clears original state, and skips duplicate hook identities while preserving reverse-order cleanup semantics.

---

## Behavior Slice: Structured Startup Event Consistency
- Why this matters: startup diagnostics must carry stable context across success/failure for downstream logging and troubleshooting.

### Checklist
- [x] Added `tests/dpost_v2/application/startup/test_bootstrap.py::test_bootstrap_success_event_includes_metadata_and_boot_timestamp`.
- [x] Added `tests/dpost_v2/application/startup/test_bootstrap.py::test_bootstrap_failure_event_is_structured_with_request_metadata`.
- [x] Updated `src/dpost_v2/application/startup/bootstrap.py` to include `mode`, `profile`, `metadata`, and `boot_timestamp_utc` in started/succeeded/failed events.

### Completion Notes
- How it was done: bootstrap now captures one deterministic boot timestamp per run and reuses request metadata consistently in startup event payloads.

---

## Files Modified
- `src/dpost_v2/__main__.py`
- `src/dpost_v2/application/startup/bootstrap.py`
- `src/dpost_v2/runtime/composition.py`
- `tests/dpost_v2/test___main__.py`
- `tests/dpost_v2/application/startup/test_bootstrap.py`
- `tests/dpost_v2/runtime/test_composition.py`

## Tests Added/Updated
- Added:
  - `tests/dpost_v2/test___main__.py::test_main_handles_non_integer_system_exit_code_deterministically`
  - `tests/dpost_v2/runtime/test_composition.py::test_composition_shutdown_hook_is_idempotent`
  - `tests/dpost_v2/application/startup/test_bootstrap.py::test_bootstrap_success_event_includes_metadata_and_boot_timestamp`
  - `tests/dpost_v2/application/startup/test_bootstrap.py::test_bootstrap_failure_event_is_structured_with_request_metadata`
  - `tests/dpost_v2/application/startup/test_bootstrap.py::test_bootstrap_cleanup_order_is_stable_for_dry_run_and_non_dry_run`

## Commands Run and Results
- `python -m pytest -q tests/dpost_v2/test___main__.py tests/dpost_v2/runtime/test_composition.py tests/dpost_v2/application/startup/test_bootstrap.py` -> `33 passed`
- `python -m ruff check src/dpost_v2 tests/dpost_v2` -> `All checks passed`
- `python -m pytest -q tests/dpost_v2` -> `367 passed`
- `git show --name-only --pretty=format:"%h %s" 890b19c` -> confirms lane slice commit contents

## Risks / Assumptions
- Assumption: startup event payload contract should expose request-level `mode/profile/metadata` consistently across success and failure paths.
- Assumption: one-shot shutdown behavior is preferred over repeated retry attempts for the same hook.
- Risk: if a shutdown hook fails once, later repeated shutdown calls do not retry by design.

## Checkpoint
- Commit: `890b19c`
- Message: `v2: stabilization-runtime-resilience startup shutdown idempotency`
