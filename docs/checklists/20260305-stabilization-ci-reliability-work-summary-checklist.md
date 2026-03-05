# Checklist: Stabilization CI Reliability Work Summary

## Section: Workflow Reliability Hardening
- Why this matters: improves CI determinism and reduces flaky failures from runner/image drift and transient dependency installs.

### Checklist
- [x] Pinned Public CI runner labels to stable images.
- [x] Pinned Rewrite CI runner labels to stable image.
- [x] Added pip retry/timeout hardening to install steps.
- [x] Added pip cache dependency keying through `pyproject.toml`.

### Manual Check
- [x] Review `.github/workflows/public-ci.yml` runner labels:
  - [x] `ubuntu-24.04`
  - [x] `windows-2022`
- [x] Review `.github/workflows/rewrite-ci.yml` runner labels:
  - [x] `ubuntu-24.04`
- [x] Confirm install commands include:
  - [x] `--retries 5`
  - [x] `--timeout 60`
- [x] Confirm `actions/setup-python@v5` uses `cache-dependency-path: pyproject.toml`.

### Completion Notes
- Updated both workflows to reduce environmental drift and transient package install failures.
- Kept logic straightforward and avoided adding brittle workflow expression branching.

---

## Section: CI Signal Enrichment
- Why this matters: preserves actionable debugging context when pytest jobs fail in CI.

### Checklist
- [x] Added JUnit report output to Public CI pytest jobs.
- [x] Added JUnit report output to Rewrite CI pytest jobs.
- [x] Added artifact upload for generated test reports.
- [x] Added package build artifact upload for post-failure build inspection.

### Manual Check
- [x] In `public-ci.yml`, confirm report generation/upload for:
  - [x] `unit-tests`
  - [x] `integration-tests`
  - [x] `bootstrap-smoke`
- [x] In `rewrite-ci.yml`, confirm report generation/upload for:
  - [x] `rewrite-v2-tests`
  - [x] `rewrite-v2-integration`
- [x] Confirm artifact upload steps use `if: always()`.

### Completion Notes
- Pytest commands now include `-ra` and `--junitxml ...` for richer test diagnostics.
- Artifacts are uploaded even on failure, improving triage for stabilization regressions.

---

## Section: Required-Check Stability
- Why this matters: avoids breaking branch protection and required-check wiring during stabilization.

### Checklist
- [x] Preserved Public CI job names.
- [x] Preserved Rewrite CI job names.
- [x] Kept rewrite integration gate condition unchanged.

### Manual Check
- [x] Compare pre/post workflow names for:
  - [x] `workflow-lint`, `quality`, `unit-tests`, `integration-tests`, `bootstrap-smoke`, `package-build`, `artifact-hygiene`
  - [x] `rewrite-workflow-lint`, `rewrite-artifact-hygiene`, `rewrite-v2-quality`, `rewrite-v2-tests`, `rewrite-v2-integration`
- [x] Confirm `rewrite-v2-integration` still uses:
  - [x] `if: github.ref == 'refs/heads/rewrite/v2' && (github.event_name == 'push' || github.event_name == 'workflow_dispatch')`

### Completion Notes
- Required-check semantics were intentionally preserved while reliability improvements were applied.

---

## Section: Validation and Closeout
- Why this matters: confirms V2 quality gate remains green after CI workflow changes.

### Checklist
- [x] Ran V2 lint locally after edits.
- [x] Ran V2 tests locally after edits.
- [x] Performed workflow YAML parse sanity check.
- [x] Captured stabilization status and risks in lane docs.

### Manual Check
- [x] `python -m ruff check src/dpost_v2 tests/dpost_v2`
  - [x] Result: `All checks passed!`
- [x] `python -m pytest -q tests/dpost_v2`
  - [x] Result: `361 passed`
- [x] YAML parse check for `.github/workflows/*.yml`
  - [x] Result: `workflow yaml parse ok`
- [x] Confirm supporting docs exist:
  - [x] `docs/checklists/20260305-stabilization-ci-reliability-checklist.md`
  - [x] `docs/reports/20260305-stabilization-ci-reliability-report.md`

### Completion Notes
- Lane changes remained within allowed scope (`.github/workflows/**`, `docs/checklists/**`, `docs/reports/**`).
- No product runtime code was modified.
