# Checklist: Public CI Implementation (OSS Baseline)

## Objective
- Create a tracked, deterministic public CI configuration under `.github/workflows` that enforces quality, tests, bootstrap hygiene, and artifact posture.

## Why this matters
- PRs need repeatable verification without manual setup.
- OSS contributors should see concrete, automated evidence for code quality and environment hygiene.

### Checklist
- [x] Confirm baseline state had no `.github/workflows` workflows before implementation.
- [x] Confirm `.github` and `.github/workflows` are not gitignored.
- [x] Confirm `.env` and `build/.env` are not tracked and are ignored.
- [x] Add a checklist + report that captures current state and proposed CI shape.
- [x] Add workflow files:
  - quality job (`ruff`, `black --check`)
  - tests job (`pytest`)
  - bootstrap smoke job (bootstrap runtime settings from env)
  - package build job (`python -m build`, optional but pinned)
  - hygiene job (`.env` tracking and workflow path checks)
- [x] Ensure workflow files themselves are tracked and visible for code review.
- [x] Validate the workflow configuration is branch/PR scoped for `main`.
- [x] Add any required docs references from planning/report artifacts.
- [x] Add a workflow lint guard (`actionlint`) so CI config changes fail fast on invalid workflow syntax.
- [x] Add `workflow_dispatch` for controlled manual execution.
- [x] Add CI hardening defaults (`timeout-minutes`, `setup-python` pip cache) for stability and runtime control.

### Completion Notes
- What was done: Added `.github/workflows/public-ci.yml`, updated `.gitignore` to explicitly unignore `.github` workflow config, and documented checklist/report artifacts for implementation visibility. Follow-up hardening added `workflow-lint`, `workflow_dispatch`, job timeouts, and pip cache in Python setup steps.
- Evidence:
  - [`.github/workflows/public-ci.yml`](/d:/Repos/ipat_data_watchdog/.github/workflows/public-ci.yml)
  - [`docs/checklists/20260303-public-ci-implementation-checklist.md`](/d:/Repos/ipat_data_watchdog/docs/checklists/20260303-public-ci-implementation-checklist.md)
  - [`docs/reports/20260303-public-ci-existing-vs-proposed-report.md`](/d:/Repos/ipat_data_watchdog/docs/reports/20260303-public-ci-existing-vs-proposed-report.md)
