# Checklist: V2 Standalone Headless Executable

## Execution Order (Start Here)
- Why this matters: The three-plugin parity phase is closed. The next blocker to
  real workstation deployment is resident runtime behavior plus frozen build
  readiness.

### Manual Check
- [x] `docs/reports/20260305-v2-three-plugin-closeout-report.md` is accepted as
  the baseline functional/runtime proof.
- [x] `build/specs/*.spec` still point at legacy `ipat_watchdog` entrypoints,
  which confirms packaging is not yet on the canonical V2 path.

### Checklist
- [x] Treat `docs/checklists/20260305-v2-three-plugin-functional-parity-checklist.md`
  as closed for the accepted plugin-parity phase.
- [x] Treat this checklist as the active next functional slice.
- [x] Treat the first two sections as single-lane only:
  - `Section: Runtime loop contract (TDD)`
  - `Section: Shutdown and lifecycle contract (TDD)`
- [x] Allow parallelization only after those two sections are green:
  - `Section: Frozen bootstrap/config path contract (TDD)`
  - `Section: PyInstaller build baseline (TDD)`
- [ ] Start execution with:
- [x] Start execution with:
  - `Section: Runtime loop contract (TDD)`
  - `Section: Shutdown and lifecycle contract (TDD)`

### Completion Notes
- How it was done:
  - Started implementation on `main` after checkpointing the standalone-slice
    planning docs in commit `b2f54f8`.

---

## Section: Baseline lock
- Why this matters: Packaging/runtime-posture work must start from the current
  closed V2 runtime, not from partial lane assumptions.

### Manual Check
- [x] `git status --short --branch` is captured in notes.
- [x] Existing runtime closeout artifacts are referenced in notes.

### Checklist
- [x] Re-use the current three-plugin closeout report as the functional baseline.
- [x] Record current packaging/build baseline:
  - `pyproject.toml`
  - `build/specs/*.spec`
  - canonical entrypoint `src/dpost/__main__.py`
- [x] Avoid changing device parity behavior in this slice unless required by the
  resident-runtime contract.

### Completion Notes
- How it was done:
  - Baseline inputs were re-checked before code changes:
    - `docs/reports/20260305-v2-three-plugin-closeout-report.md`
    - `pyproject.toml`
    - `build/specs/gen.spec`
    - `src/dpost/__main__.py`
  - Device-plugin behavior was not changed directly; the slice stayed in shared
    startup/runtime surfaces.

---

## Section: Runtime loop contract (TDD)
- Why this matters: A background workstation executable must remain resident and
  process files arriving after startup. One-shot scanning is not enough.

### Manual Check
- [ ] Headless runtime can be run in deterministic one-shot mode.
- [ ] Headless runtime can also remain alive long enough to process a file that
  appears after startup.

### Checklist
- [x] Add failing tests for explicit one-shot vs continuous runtime behavior.
- [x] Add failing tests for repeated scan cycles without duplicate processing.
- [x] Add failing tests for deterministic event ordering within a scan cycle.
- [x] Implement minimal runtime loop changes under `src/dpost_v2/application/runtime/`
  and `src/dpost_v2/runtime/`.
- [x] Keep current one-shot manual smoke path intact.

### Completion Notes
- How it was done:
  - Added runtime-loop red tests in:
    - `tests/dpost_v2/application/runtime/test_dpost_app.py`
    - `tests/dpost_v2/application/startup/test_settings_schema.py`
    - `tests/dpost_v2/application/startup/test_settings.py`
    - `tests/dpost_v2/application/startup/test_settings_service.py`
    - `tests/dpost_v2/runtime/test_composition.py`
  - Implemented explicit runtime loop policy via startup/runtime settings:
    - `oneshot`
    - `continuous`
    - `poll_interval_seconds`
  - Headless composition now re-discovers files per cycle in continuous mode.
  - One-shot runtime behavior remains green across the existing suite.

---

## Section: Shutdown and lifecycle contract (TDD)
- Why this matters: A resident executable must shut down cleanly and predictably,
  especially when running in the background on operator PCs.

### Manual Check
- [ ] Continuous mode exits cleanly on an explicit stop condition.
- [ ] Exit behavior is deterministic for success, cancellation, and runtime
  failure paths.

### Checklist
- [x] Add failing tests for stop/cancel handling in continuous headless mode.
- [ ] Add failing tests for clean adapter shutdown after continuous runs.
- [x] Add failing tests for idle/backoff timing behavior that do not depend on
  wall-clock sleeps.
- [x] Implement minimal lifecycle changes without introducing legacy runtime
  loops or hidden globals.

### Completion Notes
- How it was done:
  - Continuous runtime now uses an injected idle wait hook that prefers the
    clock adapter's `sleep()` when available, keeping timeout tests
    deterministic.
  - Added lifecycle coverage for:
    - cancellation after late-arriving work
    - idle `soft_timeout` during continuous polling
  - Clean adapter shutdown after continuous runs is still open as a distinct
    check.

---

## Section: Frozen bootstrap/config path contract (TDD)
- Why this matters: A PyInstaller executable must resolve config, paths, and
  plugin loading from the canonical V2 entrypoint the same way source execution
  does.

### Manual Check
- [ ] Source and frozen startup resolve the same config semantics for a temp
  probe workspace.
- [ ] Frozen execution does not depend on legacy `ipat_watchdog` entrypoints.

### Checklist
- [ ] Add failing tests for frozen-safe config path resolution and root handling.
- [ ] Add failing tests for packaging entrypoint expectations around
  `src/dpost/__main__.py`.
- [ ] Implement minimal startup/build changes needed for frozen-safe path
  behavior.
- [ ] Keep `python -m dpost` behavior unchanged for source execution.

### Completion Notes
- How it was done:

---

## Section: PyInstaller build baseline (TDD)
- Why this matters: The repo needs one authoritative V2 build surface for the
  standalone executable, not legacy workstation-specific specs.

### Manual Check
- [ ] A V2 PyInstaller build completes from the canonical build path.
- [ ] The built artifact can process a temp probe file in headless mode.

### Checklist
- [ ] Add a V2-specific spec or build script for the canonical `dpost` entrypoint.
- [ ] Add packaging smoke checks for the built executable.
- [ ] Validate required hidden imports/plugin surfaces for the accepted plugin set.
- [ ] Document the exact build and smoke commands in repo docs.

### Completion Notes
- How it was done:

---

## Section: Manual workstation closeout
- Why this matters: Source-level green tests are not enough for a background PC
  executable. A manual frozen probe must confirm the real operator posture.

### Manual Check
- [ ] Source `python -m dpost` continuous mode processes files arriving after
  startup.
- [ ] Frozen executable continuous mode processes files arriving after startup.
- [ ] Shutdown is clean and does not leave the runtime in a bad state.

### Checklist
- [ ] Run targeted runtime/build checks.
- [ ] Run `python -m ruff check src/dpost_v2 tests/dpost_v2`.
- [ ] Run `python -m pytest -q tests/dpost_v2`.
- [ ] Publish a standalone-executable slice report in `docs/reports/`.

### Completion Notes
- How it was done:
