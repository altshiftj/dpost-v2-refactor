# Checklist: Stabilization CI Reliability Detailed Work

## Section: Lane Scope and Guardrails
- Why this matters: keeps stabilization changes constrained to CI and documentation surfaces while protecting V2 runtime code boundaries.

### Checklist
- [x] Work executed from lane worktree path only.
- [x] Edits restricted to `.github/workflows/**`, `docs/checklists/**`, and `docs/reports/**`.
- [x] Product runtime code under `src/dpost_v2` and tests under `tests/dpost_v2` were not modified.

### Manual Check
- [x] Confirm worktree path: `D:\Repos\d-post\.worktrees\stabilization-ci-reliability`
- [x] Confirm changed files are lane-allowed paths.
- [x] Confirm no runtime/test implementation files were edited in this lane.

### Completion Notes
- [x] Lane boundaries were preserved for the full implementation.

---

## Section: Public CI Reliability Improvements
- Why this matters: reduces flake risk and improves deterministic behavior for required checks on active branches.

### Checklist
- [x] Pinned Linux runner labels from `ubuntu-latest` to `ubuntu-24.04`.
- [x] Pinned Windows runner labels from `windows-latest` to `windows-2022`.
- [x] Added pip network hardening (`--retries 5 --timeout 60`) to dependency install steps.
- [x] Added `cache-dependency-path: pyproject.toml` to Python setup cache config.

### Manual Check
- [x] Verify `.github/workflows/public-ci.yml` runner labels are pinned.
- [x] Verify pip install steps include retry/timeout options.
- [x] Verify setup-python includes dependency-keyed cache path.

### Completion Notes
- [x] Public CI now uses pinned runner images and more resilient install commands.

---

## Section: Rewrite CI Reliability Improvements
- Why this matters: keeps rewrite-lane validation stable during active stabilization while avoiding unnecessary required-check churn.

### Checklist
- [x] Pinned rewrite jobs from `ubuntu-latest` to `ubuntu-24.04`.
- [x] Added pip network hardening (`--retries 5 --timeout 60`) to rewrite quality/tests/integration jobs.
- [x] Added `cache-dependency-path: pyproject.toml` for rewrite Python setup.

### Manual Check
- [x] Verify `.github/workflows/rewrite-ci.yml` pinned runner labels.
- [x] Verify pip install steps include retry/timeout options.
- [x] Verify setup-python dependency-keyed cache path is present.

### Completion Notes
- [x] Rewrite CI now mirrors reliability hardening used in Public CI.

---

## Section: CI Signal Enrichment
- Why this matters: improves diagnosis speed by preserving structured test artifacts for failing jobs.

### Checklist
- [x] Added JUnit XML output for Public CI pytest jobs.
- [x] Added JUnit XML output for Rewrite CI pytest jobs.
- [x] Added artifact uploads for JUnit outputs with `if: always()`.
- [x] Added package-build artifact upload for build output inspection.

### Manual Check
- [x] Verify Public CI report generation/upload in:
  - [x] `unit-tests`
  - [x] `integration-tests`
  - [x] `bootstrap-smoke`
- [x] Verify Rewrite CI report generation/upload in:
  - [x] `rewrite-v2-tests`
  - [x] `rewrite-v2-integration`
- [x] Verify package build upload exists in `package-build`.

### Completion Notes
- [x] CI now emits richer debugging artifacts without adding brittle conditional logic.

---

## Section: Required-Check Stability and Branch Semantics
- Why this matters: preserves branch protection behavior while improving reliability.

### Checklist
- [x] Kept existing Public CI job names unchanged.
- [x] Kept existing Rewrite CI job names unchanged.
- [x] Kept rewrite integration branch/event gate condition unchanged.

### Manual Check
- [x] Confirm unchanged Public CI names:
  - [x] `workflow-lint`
  - [x] `quality`
  - [x] `unit-tests`
  - [x] `integration-tests`
  - [x] `bootstrap-smoke`
  - [x] `package-build`
  - [x] `artifact-hygiene`
- [x] Confirm unchanged Rewrite CI names:
  - [x] `rewrite-workflow-lint`
  - [x] `rewrite-artifact-hygiene`
  - [x] `rewrite-v2-quality`
  - [x] `rewrite-v2-tests`
  - [x] `rewrite-v2-integration`
- [x] Confirm rewrite integration gate expression remains:
  - [x] `github.ref == 'refs/heads/rewrite/v2' && (github.event_name == 'push' || github.event_name == 'workflow_dispatch')`

### Completion Notes
- [x] Required-check semantics were preserved as requested.

---

## Section: Validation Evidence and Documentation
- Why this matters: records objective lane outcomes and risk assumptions for stabilization tracking.

### Checklist
- [x] Ran `ruff` for V2 scope.
- [x] Ran `pytest` for V2 scope.
- [x] Performed workflow YAML parse sanity check.
- [x] Produced stabilization report and checklist artifacts.

### Manual Check
- [x] `python -m ruff check src/dpost_v2 tests/dpost_v2`
  - [x] Result: `All checks passed!`
- [x] `python -m pytest -q tests/dpost_v2`
  - [x] Result: `361 passed`
- [x] Workflow parse check with Python YAML loader
  - [x] Result: `workflow yaml parse ok`
- [x] Confirm supporting docs:
  - [x] `docs/checklists/20260305-stabilization-ci-reliability-checklist.md`
  - [x] `docs/checklists/20260305-stabilization-ci-reliability-work-summary-checklist.md`
  - [x] `docs/reports/20260305-stabilization-ci-reliability-report.md`

### Completion Notes
- [x] Lane produced complete workflow hardening + documentation record.
- [x] Remaining external verification is a real GitHub-hosted Actions run post-push.
