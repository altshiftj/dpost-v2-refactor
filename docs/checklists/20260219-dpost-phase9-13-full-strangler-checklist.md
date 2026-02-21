# dpost Phase 9-13 Full Strangler Checklist

## Section: Cross-phase Modernization Quality Gates
- Why this matters: Final migration work should deliver both behavior safety
  and cleaner, open-source-grade architecture quality.

### Checklist
- [x] Define/confirm functional-equivalence assertions before each
      implementation increment.
- [x] Define targeted syntactic simplifications before each increment (for
      example wrapper removal, call-path flattening, intent naming cleanup).
- [x] Reject changes that add new indirection without clear contract or
      boundary value.
- [x] Capture per-phase before/after simplification evidence in the phase
      report.
- [x] Keep architecture baseline/contract/responsibility docs aligned with
      ownership and boundary shifts.

### Completion Notes
- How it was done: Each Phase 9-13 increment used tests-first red/green loops
  with explicit simplification targets:
  runtime bootstrap contract extraction (Phase 9), runtime orchestration
  extraction to `dpost/application` (Phase 10), runtime UI infrastructure
  adapter extraction (Phase 11), plugin/config boundary extraction (Phase 12),
  and canonical startup direct-import retirement increment (Phase 13). Per-
  phase evidence is captured in reports and this checklist.

---

## Section: Phase 9 Native dpost Bootstrap Core
- Why this matters: Removing bootstrap-level legacy coupling is the first hard
  boundary needed for a truly native `dpost` runtime.

### Checklist
- [x] Add/confirm migration tests that fail when runtime bootstrap/composition
      depend on `ipat_watchdog.core.app.bootstrap`.
- [x] Introduce native `dpost` bootstrap context/settings/error contract.
- [x] Remove legacy bootstrap-module dependency from `src/dpost/runtime/bootstrap.py`.
- [x] Remove legacy bootstrap type/module dependency from
      `src/dpost/runtime/composition.py`.
- [x] Remove transition-only bootstrap indirection and keep startup behavior
      equivalent to current baseline.
- [x] Verify migration + full gates are green.

### Completion Notes
- How it was done: Tests-first contract was already in place via
  `tests/migration/test_phase9_native_bootstrap_boundary.py` and confirmed red
  with `python -m pytest tests/migration/test_phase9_native_bootstrap_boundary.py`
  -> `2 failed` before implementation. Implementation introduced native runtime
  startup contracts in `src/dpost/runtime/bootstrap.py`, moved direct legacy
  bootstrap module coupling into
  `src/dpost/infrastructure/runtime/legacy_bootstrap_adapter.py`, and removed
  legacy bootstrap type coupling from `src/dpost/runtime/composition.py`.
  Post-change boundary verification:
  `python -m pytest tests/migration/test_phase9_native_bootstrap_boundary.py`
  -> `2 passed`.
  Follow-up gate recovery removed stale plugin directories
  `src/ipat_watchdog/device_plugins/pca_granupack` and
  `src/ipat_watchdog/pc_plugins/granupack_blb`.
  Final Phase 9 gate verification:
  `python -m pytest tests/migration/test_phase9_native_bootstrap_boundary.py`
  -> `2 passed`;
  `python -m pytest -m migration`
  -> `95 passed, 302 deselected`;
  `python -m ruff check .`
  -> `All checks passed!`;
  `python -m black --check .`
  -> `43 files would be left unchanged.`;
  `python -m pytest`
  -> `396 passed, 1 skipped`.

---

## Section: Phase 10 Application Orchestration Extraction
- Why this matters: Runtime composition should orchestrate through application
  services/ports instead of legacy monolith wiring.

### Checklist
- [x] Add failing migration tests for `dpost/application` orchestration usage.
- [x] Extract orchestration entrypoints into `dpost/application` services.
- [x] Keep behavior parity for processing/session runtime paths.
- [x] Flatten orchestration call paths and replace legacy alias naming with
      intention-revealing `dpost` names.
- [x] Verify migration + full gates are green.

### Completion Notes
- How it was done: Added tests-first contract
  `tests/migration/test_phase10_application_orchestration_extraction.py`
  and captured red-state (`3 failed`). Implemented
  `src/dpost/application/services/runtime_startup.py` and rewired
  `src/dpost/runtime/composition.py` to delegate runtime orchestration through
  `compose_runtime_context()`. Green verification:
  `python -m pytest tests/migration/test_phase10_application_orchestration_extraction.py`
  -> `3 passed`, plus full migration/lint/format/full-suite gates green.
  Evidence summary is documented in:
  `docs/reports/20260221-phase10-13-runtime-boundary-progress.md`.

---

## Section: Phase 11 Infrastructure Adapter Extraction
- Why this matters: Clean adapter boundaries prevent application logic from
  drifting back into concrete integration dependencies.

### Checklist
- [x] Add failing migration tests for application-to-infrastructure boundary
      enforcement.
- [x] Move runtime/filesystem/observability glue behind `dpost/infrastructure`
      adapters and ports.
- [x] Ensure composition root owns adapter selection/wiring.
- [x] Narrow adapter APIs to explicit ports and remove transition-era helper
      sprawl.
- [x] Verify migration + full gates are green.

### Completion Notes
- How it was done: Added tests-first contract
  `tests/migration/test_phase11_runtime_infrastructure_boundary.py`
  and captured red-state (`3 failed`). Implemented
  `src/dpost/infrastructure/runtime/ui_factory.py` and rewired
  `src/dpost/runtime/composition.py` to delegate mode-specific UI selection
  via `resolve_ui_factory()` instead of direct legacy Tk imports.
  Green verification:
  `python -m pytest tests/migration/test_phase11_runtime_infrastructure_boundary.py`
  -> `3 passed`, plus full migration/lint/format/full-suite gates green.
  Evidence summary is documented in:
  `docs/reports/20260221-phase10-13-runtime-boundary-progress.md`.

---

## Section: Phase 12 Plugin and Config Boundary Migration
- Why this matters: Plugin/config ownership must live in `dpost` boundaries for
  long-term extensibility and open-source maintainability.

### Checklist
- [x] Add failing migration tests for plugin/config boundary ownership in
      `dpost`.
- [x] Migrate plugin/config startup contracts to `dpost` boundary modules.
- [x] Keep plugin discovery errors actionable and regression-tested.
- [x] Normalize plugin/config boundary naming to canonical `dpost` terms and
      remove alias indirection.
- [x] Verify migration + full gates are green.

### Completion Notes
- How it was done: Added tests-first contract
  `tests/migration/test_phase12_plugin_config_boundary_migration.py`
  and captured red-state (`3 failed`). Implemented
  `src/dpost/runtime/startup_config.py` and
  `src/dpost/plugins/profile_selection.py`, then rewired
  `src/dpost/runtime/composition.py` to use
  `resolve_runtime_startup_settings()` and
  `resolve_plugin_profile_selection()` directly in canonical composition flow.
  Green verification:
  `python -m pytest tests/migration/test_phase12_plugin_config_boundary_migration.py`
  -> `3 passed`, plus full migration/lint/format/full-suite gates green.
  Evidence summary is documented in:
  `docs/reports/20260221-phase10-13-runtime-boundary-progress.md`.

---

## Section: Phase 13 Legacy Runtime Retirement
- Why this matters: Final strangler completion requires canonical runtime paths
  to run without legacy core runtime module dependency.

### Checklist
- [x] Add failing migration tests asserting no runtime dependency on
      `src/ipat_watchdog/core/...` from canonical startup path.
- [ ] Remove remaining runtime dependency surfaces and transition-only glue.
- [ ] Confirm canonical startup path is concise and readable without legacy
      runtime context.
- [ ] Update docs/checklists/execution board to reflect legacy runtime
      retirement completion.
- [x] Verify migration + full gates are green.

### Completion Notes
- How it was done: Added tests-first contract
  `tests/migration/test_phase13_legacy_runtime_retirement.py`
  and captured red-state (`2 failed`) for canonical startup direct-import
  coupling. Implemented `src/dpost/infrastructure/logging.py` and rewired
  `src/dpost/__main__.py` to use the dpost logging adapter, removing direct
  `ipat_watchdog.core` imports from canonical startup modules.
  Green verification:
  `python -m pytest tests/migration/test_phase13_legacy_runtime_retirement.py`
  -> `2 passed`, plus full migration/lint/format/full-suite gates green.
  Remaining Phase 13 work: full retirement of legacy runtime dependency
  surfaces behind infrastructure adapters.
  Evidence summary is documented in:
  `docs/reports/20260221-phase10-13-runtime-boundary-progress.md`.

---

## Section: Manual Check
- Why this matters: Human verification confirms end-to-end runtime behavior
  after each major architectural boundary shift.

### Checklist
- [ ] Desktop manual check: startup succeeds and representative processing flow
      remains correct.
- [ ] Desktop manual check: rename, error messaging, and sync dialogs remain
      behaviorally correct.
- [ ] Headless manual check: startup/processing/observability remain functional.
- [ ] Plugin manual check: representative plugin set loads and processes across
      instrument families.
- [ ] Migration hygiene manual check: documented setup/start commands work from
      a clean environment.
- [ ] Manual architecture readability check: touched runtime/composition paths
      are understandable without transition-era wrapper tracing.

### Manual Validation Steps
1. Run desktop mode (`DPOST_RUNTIME_MODE=desktop`) and validate startup,
   processing, rename-flow, and sync error surfacing behavior.
2. Run headless mode (`DPOST_RUNTIME_MODE=headless`) and validate processing,
   metrics endpoint, and optional observability endpoint behavior.
3. Execute representative plugin spot checks for each instrument family.
4. Validate documented install/run commands from README and user/developer docs
   in a clean environment.

### Completion Notes
- How it was done: Pending.
