# Report: Public CI Baseline (Existing vs Proposed)

## Date
- 2026-03-03

## Existing State
- `.github/workflows` directory: added at
  - `/.github/workflows/public-ci.yml`
- `.github/instructions/concise_coding.instructions.md` exists.
- `.env` and `build/.env` are currently absent in working tree and deleted earlier.
- `.gitignore` currently ignores `.env` and allows `.env.example` (explicitly), and now explicitly unignores `.github/workflows`.

## Proposed State
- Add `.github/workflows/public-ci.yml` with:
  - `workflow-lint` job: `actionlint` to validate workflow syntax before downstream jobs.
  - `quality` job: `ruff` + `black --check` (Linux-hosted, direct tool installs).
  - `unit-tests` job: `pytest -q` with deterministic OSS-safe startup env.
  - `bootstrap-smoke` job: targeted bootstrap tests using `DPOST_*` environment overrides.
  - `package-build` job: `python -m build` to catch manifest/import regressions.
  - `artifact-hygiene` job:
    - ensure `.github/workflows` exists and is tracked,
    - ensure `.env` and `build/.env` are not tracked,
    - ensure `.github/workflows` is not ignored,
    - ensure `.env.example` exists.
- Trigger on `workflow_dispatch`, `push`, and `pull_request` to `main` / `master`.
- Optional follow-up split into smaller jobs after first pass stabilizes.
- Implementation updates:
  - `.github/workflows/public-ci.yml` has been added with jobs for quality, tests, bootstrap-smoke, package-build, and artifact-hygiene.
  - `.gitignore` now explicitly unignores `.github` workflow config.

## Current Implementation State
- `/.github/workflows/public-ci.yml` is present and reviewable.
- `/.github/workflows/public-ci.yml` includes:
  - `workflow-lint` (actionlint gate),
  - `quality` (ruff + black checks, Linux-hosted),
  - `tests` (pytest full suite with explicit `DPOST_*` defaults, Windows-hosted),
  - `bootstrap-smoke` (targeted bootstrap tests),
  - `package-build` (`python -m build`),
  - `hygiene` (tracked-env and ignore/path checks),
  - timeout bounds on all jobs and pip caching in Python setup steps.
- Checklist artifact exists at [`docs/checklists/20260303-public-ci-implementation-checklist.md`](20260303-public-ci-implementation-checklist.md).

## Cross-file Links
- Planning: [`docs/planning/20260303-public-ci-rpc.md`](20260303-public-ci-rpc.md)
- Checklist: [`docs/checklists/20260303-public-ci-implementation-checklist.md`](20260303-public-ci-implementation-checklist.md)

## Risk and Validation Plan
- Short-term risk: bootstrap/tests remain Windows-hosted due device/runtime dependency profile.
- Validation plan:
  - run workflow in branch mode,
  - confirm required jobs complete before merge,
  - confirm `.github/workflows/public-ci.yml` is visible and reviewable.
