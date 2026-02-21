# Coverage-Informed Architecture Findings (2026-02-21)

## Scope

This report summarizes architecture and quality findings discovered while
increasing unit coverage across `src/dpost/**` during autonomous TDD cycles.

## Validation Evidence Snapshot

Latest validated baseline in this run:

- Command:
  - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit`
- Result:
  - `503 passed, 1 skipped, 1 warning`
  - total coverage: `92%` (`4932 stmts, 414 miss`)

Additional quality gate:

- Command:
  - `python -m ruff check tests/unit`
- Result:
  - `All checks passed`

## Key Findings

### 1. Global active-config access is still a high-coupling seam

Several helpers that look local/pure still depend on `application.config.runtime.current()`
through lower-level utilities (notably storage/naming helpers). This makes tests
and runtime behavior sensitive to hidden global state and initialization ordering.

Observed impact:

- tests for otherwise simple processor helpers failed until config service was active
- path/id helper behavior can vary based on global runtime context

### 2. Runtime composition boundaries are now strongly testable

`runtime/composition.py`, `runtime/startup_config.py`,
`application/services/runtime_startup.py`, and runtime UI adapters can be tested
with stubs only. This confirms the framework-first composition posture is working
well in these areas.

### 3. Coverage gaps are now concentrated in orchestration-heavy flows

Most low/medium complexity modules are at or near 100%. Remaining misses cluster in:

- `src/dpost/application/processing/file_process_manager.py` (79%)
- `src/dpost/application/runtime/device_watchdog_app.py` (79%)
- `src/dpost/infrastructure/sync/kadi_manager.py` (63%)
- `src/dpost/plugins/system.py` (74%)
- larger device processors (`rhe_kinexus`, portions of `psa_horiba`, etc.)

These modules combine timing, filesystem, retry/deferred behavior, and integration edges.

### 4. Branch coverage improvements exposed meaningful edge behavior

High-value gains came from explicitly testing:

- fallback/error branches (decode fallback, missing files, invalid env)
- startup selection and optional-dependency branches
- stale/prune/cooldown behavior in event gates
- registration and adapter bridging contracts

### 5. Test module naming/package hygiene matters in this repository

Collection issues occurred when new tests reused module basenames in non-package
test directories. Unique test filenames (or consistent package scoping) are required
to avoid import mismatch during full-suite collection.

## Recommended Action Items

Detailed execution steps are tracked in:

- `docs/checklists/20260221-coverage-hardening-action-items-checklist.md`
- `docs/reports/20260221-coverage-to-refactor-insights-deep-dive.md`

Top priorities:

1. Introduce explicit runtime-context ports for helpers that currently read global config.
2. Extract and test pure decision functions from `file_process_manager` and `stability_tracker`.
3. Add an injectable client/factory seam around `kadi_manager` to isolate API interactions in unit tests.
4. Expand scenario-based tests for `device_watchdog_app` lifecycle and failure/recovery branches.
5. Standardize unique test module naming under `tests/unit/**` to prevent import collisions.

## Refactoring Guidance

### Refactor candidates with highest return

- `application/processing/file_process_manager.py`
  - split into smaller policy units:
    - candidate derivation
    - routing decision orchestration
    - sync side-effect dispatch
    - retry/defer state transitions
- `application/processing/stability_tracker.py`
  - separate temporal policy from storage/mutation side effects
- `infrastructure/sync/kadi_manager.py`
  - isolate resource lookup/create/upload flows behind narrow collaborator methods

### Dependency hygiene targets

- avoid implicit `current()` lookups in deep helpers where possible
- prefer explicit dependency passing from composition root through application services
- keep infrastructure-specific behavior behind adapter interfaces for deterministic tests

## Notes

- Coverage improvements in this effort were test-only and docs-only changes.
- No production behavior refactors were applied in this report cycle.

## In-Flight Slice Notes (Append-Only)

### Slice 1: Runtime/profile/adapter/unit helper expansion

- Intended action:
  - cover plugin registration wrappers and startup/runtime helper boundaries
    (`composition`, `startup_config`, `runtime_startup`, UI adapters/factory,
    headless UI, bootstrap dependency helpers)
- Expected outcome:
  - remove low-hanging 0-60% helper gaps and improve global unit baseline
- Observed outcome:
  - targeted suites green
  - global baseline moved from ~79% to ~85%

### Slice 2: Naming + sync adapter + storage staging + processing helper policies

- Intended action:
  - cover pure naming/domain helpers, application naming wrappers,
    processor factory/record flow, sync no-op + kadi adapter wrappers,
    staging-dir helpers, and additional bootstrap branches
- Expected outcome:
  - raise low/medium helper modules to near/full coverage
- Observed outcome:
  - targeted suites green
  - global baseline moved from ~85% to ~87%

### Slice 3: Medium helper gaps + runtime entrypoint + dialog edges

- Intended action:
  - close remaining small misses in abstract processor defaults, test-device processor,
    record manager/local record edges, modified-event prune branch, dialogs,
    and `dpost.__main__` execution branch
- Expected outcome:
  - convert several 96-99% modules to 100% and reduce residual helper risk
- Observed outcome:
  - targeted suites green after resolving collection conflicts
  - full baseline: `427 passed, 1 skipped`, total `88%`

### Slice 4: Filesystem utils branch/error hardening

- Intended action:
  - add explicit tests for:
    - `init_dirs` explicit-dir branch
    - record path invalid/active-device branches
    - move-item dir cleanup + fallback failure
    - record-folder wrapper call path
    - persisted-records success/error paths
- Expected outcome:
  - significantly reduce misses in `infrastructure/storage/filesystem_utils.py`
  - improve global baseline by ~1%
- Observed outcome:
  - `python -m ruff check tests/unit/infrastructure/storage/test_filesystem_utils.py` -> pass
  - `python -m pytest -q tests/unit/infrastructure/storage/test_filesystem_utils.py` -> `14 passed`
  - full checkpoint:
    - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit`
    - `436 passed, 1 skipped, 1 warning`
    - total coverage: `89%`
    - `filesystem_utils.py` improved to `93%` (10 misses remaining)

### Slice 5: Device resolver branch-completion pass

- Intended action:
  - close remaining `device_resolver` helper branches:
    - retry-delay fallback
    - empty-dir branch variants (missing/file/permission/os-error/non-empty)
    - probe exception wrapping
    - chooser and reason helper edge paths
    - no-candidate regular-file unmatched path
- Expected outcome:
  - raise `application/processing/device_resolver.py` to 100%
  - push global suite baseline to 90%
- Observed outcome:
  - targeted resolver gate:
    - `python -m pytest --cov=dpost.application.processing.device_resolver --cov-report=term-missing -q tests/unit/application/processing/test_device_resolver.py tests/unit/application/processing/test_device_resolver_eirich_variants.py`
    - `24 passed`
    - `device_resolver.py` -> `100%`
  - full checkpoint:
    - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit`
    - `460 passed, 1 skipped, 1 warning`
    - total coverage: `90%`

### Slice 6: Stability tracker branch-completion pass

- Intended action:
  - cover synchronous wait-loop edge paths and helper branches:
    - disappear/reappear grace handling
    - sentinel wait loop continuation
    - snapshot aggregation/file-missing tolerance
    - default/fallback polling and reappear settings
    - sleep no-op behavior for non-positive intervals
- Expected outcome:
  - raise `application/processing/stability_tracker.py` from 68% to near/full
  - improve global baseline by ~1%
- Observed outcome:
  - targeted gate:
    - `python -m pytest --cov=dpost.application.processing.stability_tracker --cov-report=term-missing -q tests/unit/application/processing/test_stability_tracker.py`
    - `18 passed`
    - `stability_tracker.py` -> `100%`
  - full checkpoint:
    - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit`
    - `473 passed, 1 skipped, 1 warning`
    - total coverage: `91%`

### Slice 7: Config schema/service edge hardening

- Intended action:
  - close residual branches in:
    - `application/config/schema.py`
    - `application/config/service.py`
  - with focused tests for:
    - override coercion/validation
    - defer/match guards and directory edge handling
    - activation/device lookup error paths and context behavior
    - ActiveConfig property pass-throughs
- Expected outcome:
  - push both config modules to full coverage and reduce hidden config-branch risk
- Observed outcome:
  - targeted gate:
    - `python -m pytest --cov=dpost.application.config.schema --cov=dpost.application.config.service --cov-report=term-missing -q tests/unit/application/config/test_schema_service_edges.py ...`
    - `53 passed`
    - `schema.py` -> `100%`
    - `service.py` -> `100%`

### Slice 8: Tkinter UI runtime branch-completion pass

- Intended action:
  - close remaining desktop UI adapter misses:
    - prompt-rename direct path
    - done-dialog replacement path
    - cancel-task no-handle/error guards
    - `run_on_ui` scheduling and `run_main_loop` delegation
- Expected outcome:
  - raise `infrastructure/runtime/tkinter_ui.py` to 100%
  - push global suite to 92%
- Observed outcome:
  - targeted gate:
    - `python -m pytest --cov=dpost.infrastructure.runtime.tkinter_ui --cov-report=term-missing -q tests/unit/infrastructure/runtime/test_ui_tkinter.py`
    - `21 passed`
    - `tkinter_ui.py` -> `100%`
  - full checkpoint:
    - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit`
    - `503 passed, 1 skipped, 1 warning`
    - total coverage: `92%`
