# Report: V2 CI Gates Lane Implementation

## Date
- 2026-03-04

## Lane
- `ci-v2-gates`

## Scope
- Maintain CI gates for growing V2 implementation coverage.
- Preserve strict required checks on `main` while keeping rewrite-branch checks lightweight.

## Files Changed
- `.github/workflows/public-ci.yml`
- `.github/workflows/rewrite-ci.yml`
- `docs/planning/20260303-v2-codex-github-parallelization-runbook-rpc.md`
- `docs/planning/20260304-v2-ci-gates-alignment-rpc.md`
- `docs/reports/20260304-v2-ci-v2-gates-lane-implementation-report.md`

## CI Behavior Changes
1. `Public CI` (`main`/`master`) keeps required check names unchanged and now fails closed on active V2 paths.
- `quality` validates `src/dpost_v2` plus `tests/dpost_v2` when present.
- `unit-tests` runs `tests/dpost_v2` directly.
- `integration-tests` runs explicit V2 integration/smoke targets under `tests/dpost_v2`.
- `bootstrap-smoke` runs bootstrap-focused tests under `tests/dpost_v2`.
2. `Rewrite CI` remains lightweight for lane branches and now includes V2 signal checks.
- `rewrite-v2-quality`: ruff + black over V2 source/tests.
- `rewrite-v2-tests`: quick V2 suite (`tests/dpost_v2` excluding smoke).
3. `Rewrite CI` adds trunk-only integration reinforcement.
- `rewrite-v2-integration` runs on `rewrite/v2` push/manual-dispatch with integration/smoke targets.

## Validation Evidence
- `python -m pytest -q tests/dpost_v2` -> `313 passed`
- `python -m ruff check src/dpost_v2 tests/dpost_v2` -> `All checks passed!`
- YAML parse sanity:
  - `.github/workflows/public-ci.yml` parsed successfully
  - `.github/workflows/rewrite-ci.yml` parsed successfully

## Risks and Assumptions
- `integration-tests` and `rewrite-v2-integration` currently use explicit target lists; new integration/smoke suites should be added to those lists intentionally.
- `rewrite-v2-integration` intentionally does not run for lane-branch pushes to keep feedback latency low.
- No GitHub-hosted run was executed from this workspace, so final timing/queue behavior should be confirmed in Actions after merge.
