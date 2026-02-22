# Coverage Hardening Action Items Checklist (2026-02-21)

## 1. Remove Hidden Global-Config Coupling

Why this matters: implicit `current()` dependencies make helper behavior context-sensitive,
increase startup-order risk, and block isolated unit testing.

- [ ] Inventory helper functions that indirectly read active global config from
      storage/naming utilities.
      Progress: identified and started addressing `filesystem_utils`,
      `session_manager`, and device-plugin `_id_separator()` helpers.
      `session_manager` + Kinexus/PSA helper slices now completed.
- [ ] Introduce explicit context/dependency parameters for those helpers
      (separator/pattern/path policy inputs).
      Progress: `filesystem_utils` path/persistence helpers now accept explicit
      separators/paths/device context while preserving legacy signatures;
      `SessionManager` now accepts explicit timeout provider.
- [ ] Update composition root wiring so concrete runtime values are provided once
      at boundaries, not pulled globally in deep helpers.
- [ ] Add focused unit tests for both explicit-context success and missing-context
      failure behavior.

## 2. Decompose Heavy Processing Orchestrators

Why this matters: coverage is now concentrated in large orchestration modules where
behavior regressions are most costly (`file_process_manager`, `stability_tracker`).

- [ ] Extract pure policy functions from `file_process_manager`:
      route/defer decisions, retry policy, force-path sync rules.
      Progress: candidate metadata, force-path sync rules, and rename retry
      policy are extracted; route-context and failure classification seams are
      extracted; remaining work is failure event/outcome side-effect separation.
- [ ] Extract time-based decision helpers from `stability_tracker` into small,
      side-effect-free units.
      Progress: timing/config resolution moved to `stability_timing_policy.py`;
      remaining work is deeper wait-loop state/event decomposition if pursued.
- [ ] Add red/green tests for extracted policy functions before refactoring call sites.
- [ ] Keep integration-level tests for orchestration glue after extraction.

## 3. Harden Sync Adapter/Manager Testability

Why this matters: `kadi_manager` remains a low-coverage high-risk adapter with external
API interactions and multi-step resource orchestration.

- [x] Add an injectable Kadi client factory boundary in `kadi_manager`.
- [x] Unit test each private flow deterministically:
      resource prep, user/group/collection creation, upload error handling.
- [x] Keep one smoke contract test for end-to-end adapter delegation semantics.

## 4. Expand Runtime Lifecycle Scenario Coverage

Why this matters: `device_watchdog_app` still has significant untested lifecycle and
failure/recovery branches that affect runtime stability.

- [x] Add lifecycle tests for startup, watcher loop transitions, graceful shutdown.
- [x] Add failure-path tests for observer errors, processing exceptions, and retry flow.
- [x] Validate UI interaction/scheduler side effects in headless-compatible unit tests.

## 5. Standardize Test Module Naming Hygiene

Why this matters: duplicate `test_*.py` basenames in non-package directories caused
import mismatch errors during full-suite collection.

- [ ] Enforce unique test module basenames across `tests/unit/**` (or consistent package
      scoping with `__init__.py` where appropriate).
- [ ] Add a lightweight guard test or lint script that fails on conflicting basenames.
- [ ] Document test naming rule in contributor testing guidance.

## Manual Check

Why this matters: manual verification ensures coverage-focused refactors still preserve
real runtime behavior and contributor workflow expectations.

- [x] Run:
      `python -m ruff check tests/unit`
- [x] Run:
      `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit`
- [x] Confirm target modules improved:
      `application/processing/file_process_manager.py`,
      `application/runtime/device_watchdog_app.py`,
      `infrastructure/sync/kadi_manager.py`,
      key device processor modules (`psa_horiba`, `rhe_kinexus`, `utm_zwick`, `erm_hioki`).
- [x] Confirm no import-mismatch collection failures across full `tests/unit`.
- [ ] Perform one operator-style smoke run in headless mode after refactors.

## Completion Notes

How it was done:

- Built from iterative red/green coverage runs during 2026-02-21 autonomous TDD sessions.
- Derived priorities from latest full coverage snapshot:
  - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit`
  - `662 passed, 1 skipped, 1 warning, total 100% (5100 stmts, 0 miss)`.
- Priorities now focus on refactor leverage and dependency cleanup rather than
  raw coverage gaps.
- Captured deeper rationale in:
  - `docs/reports/20260221-coverage-informed-architecture-findings.md`.
  - `docs/reports/20260221-coverage-to-refactor-insights-deep-dive.md`.
