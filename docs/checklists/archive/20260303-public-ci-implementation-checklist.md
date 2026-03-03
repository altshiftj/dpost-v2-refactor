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
  - unit-tests job (`pytest -q tests/unit`)
  - integration-tests job (`pytest -q tests/integration`)
  - bootstrap smoke job (bootstrap runtime settings from env)
  - package build job (`python -m build`, optional but pinned)
  - hygiene job (`.env` tracking and workflow path checks)
- [x] Ensure workflow files themselves are tracked and visible for code review.
- [x] Validate the workflow configuration is branch/PR scoped for `main`.
- [x] Add any required docs references from planning/report artifacts.
- [x] Add a workflow lint guard (`actionlint`) so CI config changes fail fast on invalid workflow syntax.
- [x] Add `workflow_dispatch` for controlled manual execution.
- [x] Add CI hardening defaults (`timeout-minutes`, `setup-python` pip cache) for stability and runtime control.
- [x] Stabilize check names for branch protection mapping (`quality (py3.12/py3.13)`, `unit-tests (py3.12/py3.13)`, `integration-tests (py3.12)`).
- [x] Add a versioned branch protection payload for `main` under `.github/branch-protection`.
- [x] Add a one-command PowerShell apply script for GitHub branch protection.
- [x] Exclude manual smoke tests from default pytest runs and keep them explicitly invokable (`-m manual`).

### Completion Notes
- What was done: Added `.github/workflows/public-ci.yml`, updated `.gitignore` to explicitly unignore `.github` workflow config, and documented checklist/report artifacts for implementation visibility. Follow-up hardening added `workflow-lint`, `workflow_dispatch`, job timeouts, and pip cache in Python setup steps.
- How it was done: Workflow job names were made deterministic for branch-protection contexts; test execution was split into explicit `unit` and `integration` lanes; required-check payload and GitHub API apply script were added in-repo so branch protection can be applied reproducibly when the repository is hosted on GitHub.
- Evidence:
  - [`.github/workflows/public-ci.yml`](../../.github/workflows/public-ci.yml)
  - [`.github/branch-protection/main.required-checks.json`](../../.github/branch-protection/main.required-checks.json)
  - [`scripts/github/set-main-branch-protection.ps1`](../../scripts/github/set-main-branch-protection.ps1)
  - [`docs/checklists/20260303-public-ci-implementation-checklist.md`](20260303-public-ci-implementation-checklist.md)
  - [`docs/reports/20260303-public-ci-existing-vs-proposed-report.md`](../reports/20260303-public-ci-existing-vs-proposed-report.md)

### Manual Check
- Run `pwsh -File scripts/github/set-main-branch-protection.ps1 -Repository owner/repo` with `GITHUB_TOKEN` set.
- Open GitHub branch settings for `main` and verify required checks match `.github/branch-protection/main.required-checks.json`.
