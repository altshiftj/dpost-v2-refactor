# Coverage-Informed Architecture Findings (2026-02-21)

## Scope

This report summarizes architecture and quality findings discovered while
increasing unit coverage across `src/dpost/**` during autonomous TDD cycles.

## Validation Evidence Snapshot

Latest validated baseline in this run:

- Command:
  - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit`
- Result:
  - `427 passed, 1 skipped, 1 warning`
  - total coverage: `88%` (`4932 stmts, 581 miss`)

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
- `src/dpost/application/processing/stability_tracker.py` (68%)
- `src/dpost/infrastructure/sync/kadi_manager.py` (63%)
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
