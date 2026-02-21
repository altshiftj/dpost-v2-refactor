# Overnight Refactor Execution Checklist (2026-02-21)

## 1. Run Setup and Baseline

Why this matters: lock the starting quality state so overnight work can be
evaluated against objective evidence.

- [ ] Confirm baseline command/result snapshot is current:
      `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit`
- [ ] Confirm active refactor queue ordering is aligned with roadmap.
- [ ] Confirm active findings report path is writable:
      `docs/reports/20260221-coverage-informed-architecture-findings.md`

## 2. File Process Manager Slices

Why this matters: this remains a high-risk orchestration hotspot and biggest
return area for maintainability and regression control.

- [ ] Extract one additional pure policy seam from `file_process_manager`.
- [ ] Add focused tests only for changed/introduced seam behavior.
- [ ] Validate with targeted `ruff` + targeted `pytest`.
- [ ] Append concise slice note (intended/expected/observed + commands).

## 3. Kadi Manager Slices

Why this matters: sync behavior must be robust while removing hidden config and
tight runtime coupling.

- [ ] Continue explicit dependency/seam extraction in `kadi_manager`.
- [ ] Keep adapter behavior unchanged at public method boundaries.
- [ ] Add/adjust sync unit tests for new seam contracts.
- [ ] Append concise slice note to findings report.

## 4. Watchdog Runtime Slices

Why this matters: lifecycle and retry/error handling directly affect runtime
stability and operator experience.

- [ ] Extract one runtime lifecycle helper seam per slice.
- [ ] Keep UI/observer/scheduler side effects at runtime boundary.
- [ ] Expand deterministic unit tests for affected branches only.
- [ ] Append concise slice note to findings report.

## 5. Plugin System Slices

Why this matters: plugin discovery is environment-sensitive and must remain
predictable across deployment configurations.

- [ ] Close remaining discovery/registration edge branches in `plugins/system`.
- [ ] Prefer injected discovery/import seams over global monkeypatching.
- [ ] Keep plugin error messages contract-tested.
- [ ] Append concise slice note to findings report.

## 6. Checkpoint Discipline

Why this matters: periodic full gates catch cross-slice regressions that
targeted tests can miss.

- [ ] Run full checkpoint every 2-3 slices:
      `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit`
- [ ] If coverage combine mode conflict occurs:
      `python -m coverage erase`
      then rerun full checkpoint.
- [ ] Update roadmap/checklist progress after each full checkpoint.

## Manual Check

Why this matters: end-of-run verification confirms behavior safety and makes
handoff concise and actionable.

- [ ] Run:
      `python -m ruff check .`
- [ ] Run:
      `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit`
- [ ] Confirm no blocker-level failures in:
      `file_process_manager`, `kadi_manager`, `device_watchdog_app`, `plugins/system`.
- [ ] Confirm findings report includes append-only notes for all completed slices.

## Completion Notes

How it was done:

- [ ] Completed overnight slices recorded with command evidence.
- [ ] Final coverage and pass/fail status recorded.
- [ ] Remaining backlog prioritized for next run.
