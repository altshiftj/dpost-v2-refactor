# Overnight Refactor Run Roadmap (2026-02-21)

## Objective

Run an autonomous, multi-slice overnight refactor focused on high-risk
orchestration areas while preserving runtime behavior and sustaining/improving
unit coverage.

## Starting Baseline

- Full checkpoint command:
  - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit`
- Starting result:
  - `537 passed, 1 skipped, 1 warning`
  - `93%` total coverage (`4990 stmts, 341 miss`)

## Progress Checkpoints

### Checkpoint A: File process manager force-path seam slice

- Completed slice:
  - extracted `force_path_policy` seam from
    `src/dpost/application/processing/file_process_manager.py`
  - added focused branch tests:
    - `tests/unit/application/processing/test_force_path_policy.py`
    - `tests/unit/application/processing/test_file_process_manager_branches.py`
- Validation:
  - targeted `ruff` and targeted `pytest` passed
  - targeted coverage:
    - `file_process_manager.py` -> `99%`
    - `force_path_policy.py` -> `100%`
- Full checkpoint:
  - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit`
  - `558 passed, 1 skipped, 1 warning`
  - `94%` total coverage (`5010 stmts, 285 miss`)

### Checkpoint B: Kadi manager seam + branch-completion slice

- Completed slice:
  - added explicit `db_manager_factory` seam in
    `src/dpost/infrastructure/sync/kadi_manager.py`
  - added focused branch suite:
    - `tests/unit/infrastructure/sync/test_sync_kadi_branches.py`
- Validation:
  - targeted `ruff` and targeted sync tests passed
  - targeted coverage:
    - `kadi_manager.py` -> `100%`
- Full checkpoint:
  - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit`
  - `574 passed, 1 skipped, 1 warning`
  - `96%` total coverage (`5011 stmts, 225 miss`)

### Checkpoint C: Kinexus device processor branch-hardening slice

- Completed slice:
  - added focused branch suite:
    - `tests/unit/device_plugins/rhe_kinexus/test_file_processor_branches.py`
- Validation:
  - targeted `ruff` and targeted Kinexus tests passed
  - targeted coverage:
    - `rhe_kinexus/file_processor.py` -> `99%`
- Full checkpoint:
  - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit`
  - `593 passed, 1 skipped, 1 warning`
  - `97%` total coverage (`5011 stmts, 138 miss`)

### Checkpoint D: PSA Horiba processor branch-hardening slice

- Completed slice:
  - added focused branch suite:
    - `tests/unit/device_plugins/psa_horiba/test_file_processor_branches.py`
- Validation:
  - targeted `ruff` and targeted PSA tests passed
  - targeted coverage:
    - `psa_horiba/file_processor.py` -> `99%`
- Full checkpoint:
  - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit`
  - `609 passed, 1 skipped, 1 warning`
  - `98%` total coverage (`5011 stmts, 84 miss`)

### Checkpoint E: Residual branch-closure sprint (SEM/DSV + runtime/plugin)

- Completed slices:
  - added:
    - `tests/unit/device_plugins/sem_phenomxl2/test_file_processor_branches.py`
    - `tests/unit/device_plugins/dsv_horiba/test_dsv_file_processor_branches.py`
    - `tests/unit/application/runtime/test_device_watchdog_app_branches.py`
    - `tests/unit/plugins/system/test_plugin_loader_residual_branches.py`
- Validation:
  - targeted module coverage results:
    - `sem_phenomxl2/file_processor.py` -> `100%`
    - `dsv_horiba/file_processor.py` -> `100%`
    - `device_watchdog_app.py` -> `100%`
    - `plugins/system.py` -> `100%`
- Full checkpoint:
  - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit`
  - `627 passed, 1 skipped, 1 warning`
  - `99%` total coverage (`5011 stmts, 44 miss`)

### Checkpoint F: Final processor closure sprint (ERM/UTM + Kinexus/PSA micro-branches)

- Completed slices:
  - added:
    - `tests/unit/device_plugins/erm_hioki/test_file_processor_branches.py`
    - `tests/unit/device_plugins/utm_zwick/test_file_processor_branches.py`
  - updated:
    - `tests/unit/device_plugins/rhe_kinexus/test_file_processor_branches.py`
    - `tests/unit/device_plugins/psa_horiba/test_file_processor_branches.py`
- Validation:
  - targeted module coverage results:
    - `erm_hioki/file_processor.py` -> `100%`
    - `utm_zwick/file_processor.py` -> `100%`
    - `rhe_kinexus/file_processor.py` -> `100%`
    - `psa_horiba/file_processor.py` -> `100%`
- Full checkpoint:
  - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit`
  - `640 passed, 1 skipped, 1 warning`
  - `99%` total coverage (`5011 stmts, 1 miss`)
  - remaining residual:
    - `src/dpost/application/processing/file_process_manager.py:145` (likely unreachable defensive raise)

### Checkpoint G: File process manager policy seam closure + full-coverage checkpoint

- Completed slices:
  - added:
    - `src/dpost/application/processing/rename_retry_policy.py`
    - `tests/unit/application/processing/test_rename_retry_policy.py`
  - updated:
    - `src/dpost/application/processing/file_process_manager.py`
    - `tests/unit/application/processing/test_file_process_manager_branches.py`
- Validation:
  - targeted module coverage results:
    - `file_process_manager.py` -> `100%`
    - `rename_retry_policy.py` -> `100%`
- Full checkpoint:
  - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit`
  - `643 passed, 1 skipped, 1 warning`
  - `100%` total coverage (`5025 stmts, 0 miss`)

### Checkpoint H: Architecture-oriented seam extraction after full coverage (stability/failure policies)

- Completed slices:
  - added:
    - `src/dpost/application/processing/stability_timing_policy.py`
    - `tests/unit/application/processing/test_stability_timing_policy.py`
    - `src/dpost/application/processing/failure_outcome_policy.py`
    - `tests/unit/application/processing/test_failure_outcome_policy.py`
  - updated:
    - `src/dpost/application/processing/stability_tracker.py`
    - `src/dpost/application/processing/file_process_manager.py`
- Validation:
  - targeted module coverage results:
    - `stability_tracker.py` -> `100%`
    - `stability_timing_policy.py` -> `100%`
    - `file_process_manager.py` -> `100%`
    - `failure_outcome_policy.py` -> `100%`
- Full checkpoint:
  - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit`
  - `650 passed, 1 skipped, 1 warning`
  - `100%` total coverage (`5061 stmts, 0 miss`)

## Active Refactor Queue

1. `src/dpost/application/processing/file_process_manager.py`
   - extract remaining route-context policy seam
   - continue separating failure handling side-effect emission from outcome construction
2. deep helper global-config access cleanup (`current()/get_service()` reduction)
3. shared retry policy unification across resolver/watchdog flows
4. test naming/import hygiene automation (prevent duplicate-basename regressions)

## Execution Model

- Slice size:
  - one bounded ownership seam per slice (not broad rewrites)
- Test strategy:
  - targeted red/green tests for each extracted seam
  - avoid speculative broad test expansions unrelated to changed behavior
- Validation strategy:
  - targeted `ruff` + targeted `pytest` per slice
  - full coverage checkpoint every 2-3 slices or after risky changes
- Documentation strategy:
  - append concise intended/expected/observed slice note in:
    - `docs/reports/20260221-coverage-informed-architecture-findings.md`

## Planned Phases

## Phase 1: File Processing Orchestration Decomposition

- Extract route/rename retry policy helpers from manager pipeline.
- Extract force-path post-persist side-effect policy into explicit unit.
- Keep manager as orchestration shell with explicit collaborator seams.

Exit criteria:

- No behavior regression in existing file-process manager tests.
- New extracted helpers have focused deterministic unit tests.

## Phase 2: Kadi Manager Resource and Upload Policy Isolation

- Continue reducing cross-cutting concerns in `kadi_manager`:
  - resource naming policy
  - collection/group creation wrappers
  - upload decision/cleanup policy
- Preserve adapter behavior while improving test seam clarity.

Exit criteria:

- Existing sync tests remain green.
- New seams reduce need for implicit runtime config state.

## Phase 3: Watchdog Runtime Lifecycle Clarification

- Separate queue event handling, retry planning, and exception-shutdown behavior
  into smaller testable units.
- Keep UI/scheduler/observer side effects at runtime boundary.

Exit criteria:

- Existing runtime app tests remain green.
- Coverage in runtime orchestration path remains stable or improves.

## Phase 4: Plugin Loader Final Edge Hardening

- Complete remaining low-covered branches in plugin discovery/registration paths.
- Keep dynamic import behavior explicit and test-injectable.

Exit criteria:

- Plugin system edge tests are deterministic and green.
- Loader error paths are contract-tested with clear messages.

## Checkpoint Commands

- Targeted lint:
  - `python -m ruff check <touched files>`
- Targeted tests:
  - `python -m pytest -q <touched test files>`
- Full checkpoint:
  - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit`
- Coverage reset (if mode mismatch occurs):
  - `python -m coverage erase`

## Stop Conditions

- Requirements become ambiguous or contradictory.
- Architecture contract conflict requires a decision.
- Safety risk (potential destructive behavior) is detected.

## End-of-Run Deliverables

- Updated source/tests for completed slices.
- Updated findings report with append-only slice notes.
- Updated checklist status for completed/remaining tasks.
- One concise end-of-run summary with:
  - completed slices
  - validation evidence
  - remaining high-risk backlog
