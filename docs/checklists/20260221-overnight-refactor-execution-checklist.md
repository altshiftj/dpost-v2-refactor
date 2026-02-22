# Overnight Refactor Execution Checklist (2026-02-21)

## 1. Run Setup and Baseline

Why this matters: lock the starting quality state so overnight work can be
evaluated against objective evidence.

- [x] Confirm baseline command/result snapshot is current:
      `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit`
- [x] Confirm active refactor queue ordering is aligned with roadmap.
- [x] Confirm active findings report path is writable:
      `docs/reports/20260221-coverage-informed-architecture-findings.md`

## 2. File Process Manager Slices

Why this matters: this remains a high-risk orchestration hotspot and biggest
return area for maintainability and regression control.

- [x] Extract one additional pure policy seam from `file_process_manager`.
- [x] Add focused tests only for changed/introduced seam behavior.
- [x] Validate with targeted `ruff` + targeted `pytest`.
- [x] Append concise slice note (intended/expected/observed + commands).

## 3. Kadi Manager Slices

Why this matters: sync behavior must be robust while removing hidden config and
tight runtime coupling.

- [x] Continue explicit dependency/seam extraction in `kadi_manager`.
- [x] Keep adapter behavior unchanged at public method boundaries.
- [x] Add/adjust sync unit tests for new seam contracts.
- [x] Append concise slice note to findings report.

## 4. Watchdog Runtime Slices

Why this matters: lifecycle and retry/error handling directly affect runtime
stability and operator experience.

- [x] Extract one runtime lifecycle helper seam per slice.
- [x] Keep UI/observer/scheduler side effects at runtime boundary.
- [x] Expand deterministic unit tests for affected branches only.
- [x] Append concise slice note to findings report.

## 5. Plugin System Slices

Why this matters: plugin discovery is environment-sensitive and must remain
predictable across deployment configurations.

- [x] Close remaining discovery/registration edge branches in `plugins/system`.
- [x] Prefer injected discovery/import seams over global monkeypatching.
- [x] Keep plugin error messages contract-tested.
- [x] Append concise slice note to findings report.

## 6. Checkpoint Discipline

Why this matters: periodic full gates catch cross-slice regressions that
targeted tests can miss.

- [x] Run full checkpoint every 2-3 slices:
      `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit`
- [ ] If coverage combine mode conflict occurs:
      `python -m coverage erase`
      then rerun full checkpoint.
- [x] Update roadmap/checklist progress after each full checkpoint.

## Manual Check

Why this matters: end-of-run verification confirms behavior safety and makes
handoff concise and actionable.

- [x] Run:
      `python -m ruff check .`
- [x] Run:
      `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit`
- [x] Confirm no blocker-level failures in:
      `file_process_manager`, `kadi_manager`, `device_watchdog_app`, `plugins/system`.
- [x] Confirm findings report includes append-only notes for all completed slices.

## Completion Notes

How it was done:

- [x] Completed overnight slices recorded with command evidence.
- [x] Final coverage and pass/fail status recorded.
- [x] Remaining backlog prioritized for next run.
- [x] Final checkpoint reached:
      `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit`
      -> `662 passed, 1 skipped, 1 warning`, `100%` (`5100 stmts, 0 miss`)
- [x] Final residual in `file_process_manager` classified and documented via
      explicit `# pragma: no cover` defensive exhaustiveness guard rationale.
- [x] Post-coverage refactor slices (`stability_timing_policy`, `failure_outcome_policy`)
      completed with full-checkpoint regression confirmation still at `100%`.
- [x] Continued post-coverage `file_process_manager` seam extraction
      (`route_context_policy`, expanded failure outcome classification) with full
      checkpoint regression confirmation still at `100%`.
- [x] Began deep global-config cleanup with `filesystem_utils` explicit-context
      parameters and maintained full-checkpoint `100%` coverage.
- [x] Continued deep global-config cleanup with `SessionManager` timeout-provider
      seam and Kinexus/PSA lazy separator seams (full-checkpoint `100%` retained).
