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
- [x] Allow parallelization only after the runtime/lifecycle/host sections are green:
  - `Section: RuntimeHost refactor (TDD)`
  - `Section: Frozen bootstrap/config path contract (TDD)`
  - `Section: PyInstaller build baseline (TDD)`
- [x] Start execution with:
  - `Section: Runtime loop contract (TDD)`
  - `Section: Shutdown and lifecycle contract (TDD)`
- [x] Treat the current shutdown implementation as a behavioral checkpoint, not
  the final architecture for packaging/service work.
- [x] Insert `Section: RuntimeHost refactor (TDD)` before frozen/bootstrap and
  PyInstaller work.

### Completion Notes
- How it was done:
  - Started implementation on `main` after checkpointing the standalone-slice
    planning docs in commit `b2f54f8`.
  - After the lifecycle slice went green, the next architecture step was
    corrected: frozen/bootstrap work is now blocked on a clean `RuntimeHost`
    refactor.

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
    - `idle_timeout_seconds`
    - `max_runtime_seconds`
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
- [x] Add failing tests for clean adapter shutdown after continuous runs.
- [x] Add failing tests for idle/backoff timing behavior that do not depend on
  wall-clock sleeps.
- [x] Implement minimal lifecycle changes without introducing legacy runtime
  loops or hidden globals.

### Completion Notes
- How it was done:
  - Added lifecycle red tests in:
    - `tests/dpost_v2/application/runtime/test_dpost_app.py`
    - `tests/dpost_v2/runtime/test_composition.py`
    - `tests/dpost_v2/test___main__.py`
  - `DPostApp` now exposes an idempotent `shutdown()` hook.
  - Runtime composition passes one shared shutdown hook into both:
    - the default `DPostApp`
    - `CompositionBundle.shutdown_all`
  - The CLI now invokes runtime shutdown in a `finally` path after non-dry-run
    execution, covering:
    - successful runtime completion
    - runtime exception
    - `KeyboardInterrupt`
  - Shutdown failure after an otherwise successful runtime now returns exit code
    `1` and prints a deterministic `runtime shutdown failed` error.
  - Continuous runtime still uses the injected idle wait hook that prefers the
    clock adapter's `sleep()` when available, keeping timeout tests
    deterministic.
  - This section is accepted as the behavior checkpoint that was then promoted
    into the cleaner `RuntimeHost` architecture in the next section.

---

## Section: RuntimeHost refactor (TDD)
- Why this matters: The current app-owned shutdown seam is good enough for
  behavior, but not the cleanest lifecycle ownership model for a robust
  workstation executable or future service posture.

### Manual Check
- [ ] CLI/bootstrap consume a first-class runtime host rather than treating the
  app object as the lifecycle owner.
- [ ] `DPostApp` is no longer the canonical owner of adapter cleanup.

### Checklist
- [x] Add failing tests for a first-class `RuntimeHost` contract.
- [x] Add failing tests for composition returning a host-owned runtime handle.
- [x] Add failing CLI/bootstrap tests that consume the host contract.
- [x] Refactor runtime composition/bootstrap/CLI to use `RuntimeHost` as the
  lifecycle owner.
- [x] Remove or de-canonicalize the current app-owned shutdown seam.

### Completion Notes
- How it was done:
  - Added host-contract red tests in:
    - `tests/dpost_v2/application/runtime/test_runtime_host.py`
    - `tests/dpost_v2/runtime/test_composition.py`
    - `tests/dpost_v2/application/startup/test_bootstrap.py`
    - `tests/dpost_v2/smoke/test_bootstrap_harness_smoke.py`
  - Introduced first-class `RuntimeHost` ownership in:
    - `src/dpost_v2/application/runtime/runtime_host.py`
    - `src/dpost_v2/runtime/composition.py`
    - `src/dpost_v2/application/startup/bootstrap.py`
  - `DPostApp` no longer carries the final shutdown responsibility.
  - `CompositionBundle.app` remains available for diagnostics and tests, but the
    canonical runtime handle now reaches bootstrap/CLI through
    `CompositionBundle.runtime_handle`.
  - This section is now the architectural gate before frozen/bootstrap and
    PyInstaller work.

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
- [x] Add failing tests for frozen-safe config path resolution and root handling.
- [x] Add failing tests for packaging entrypoint expectations around
  `src/dpost/__main__.py`.
- [x] Implement minimal startup/build changes needed for frozen-safe path
  behavior.
- [x] Keep `python -m dpost` behavior unchanged for source execution.
- [x] Do not start this section until `Section: RuntimeHost refactor (TDD)` is
  green.

### Completion Notes
- How it was done:
  - Added frozen-path red tests in:
    - `tests/dpost_v2/application/startup/test_settings_service.py`
    - `tests/dpost_v2/test___main__.py`
  - When `config_path` is supplied, relative `paths.*` now anchor to the config
    file directory instead of the bootstrap root hint.
  - The V2 CLI now computes a deterministic bootstrap root hint:
    - source mode -> current working directory
    - frozen mode -> executable directory
  - Existing canonical-entrypoint delegation coverage for `src/dpost/__main__.py`
    remains green while the V2 CLI contract now carries the frozen-safe path
    behavior.
  - No PyInstaller spec/build work was done in this section; this slice stops at
    source/frozen startup-path parity.

---

## Section: PyInstaller build baseline (TDD)
- Why this matters: The repo needs one authoritative V2 build surface for the
  standalone executable, not legacy workstation-specific specs.

### Manual Check
- [x] A V2 PyInstaller build completes from the canonical build path.
- [x] The built artifact can process a temp probe file in headless mode.

### Checklist
- [x] Add a V2-specific spec or build script for the canonical `dpost` entrypoint.
- [x] Add packaging smoke checks for the built executable.
- [x] Validate required hidden imports/plugin surfaces for the accepted plugin set.
- [x] Document the exact build and smoke commands in repo docs.
- [x] Do not start this section until `Section: RuntimeHost refactor (TDD)` is
  green.

### Completion Notes
- How it was done:
  - Added the canonical packaging helper/test surface:
    - `src/dpost_v2/infrastructure/build/pyinstaller_baseline.py`
    - `tests/dpost_v2/infrastructure/build/test_pyinstaller_baseline.py`
  - Added the canonical V2 build entrypoints:
    - `build/specs/dpost_v2_headless.spec`
    - `scripts/build-v2-headless.ps1`
    - `scripts/smoke-v2-headless-exe.ps1`
  - The canonical build surface now supports two explicit variants:
    - default background/windowless build
    - debug console build via `-DebugConsole`
  - The spec now targets `src/dpost/__main__.py`, not legacy
    `ipat_watchdog` entrypoints.
  - Hidden-import collection is restricted to the accepted plugin baseline:
    - `psa_horiba`
    - `sem_phenomxl2`
    - `utm_zwick`
    - `horiba_blb`
    - `tischrem_blb`
    - `zwick_blb`
  - A real PyInstaller build completed and the built executable processed a
    temp `.tif` probe under `tischrem_blb`, proving:
    - frozen plugin discovery worked
    - frozen config-file-relative path anchoring worked
    - the persisted record resolved `plugin_id = sem_phenomxl2`

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
