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

## Active Refactor Queue

1. `src/dpost/application/processing/file_process_manager.py`
2. `src/dpost/infrastructure/sync/kadi_manager.py`
3. `src/dpost/application/runtime/device_watchdog_app.py`
4. `src/dpost/plugins/system.py`

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
