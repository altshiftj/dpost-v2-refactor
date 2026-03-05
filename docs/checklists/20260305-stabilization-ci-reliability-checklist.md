# Checklist: Stabilization CI Reliability (V2)

## Section: Baseline V2 Signal Check
- Why this matters: ensures reliability changes are applied against a known-green V2 lint/test baseline.

### Checklist
- [x] Confirm V2 lint baseline before workflow edits.
- [x] Confirm V2 test baseline before workflow edits.
- [x] Confirm lane worktree is clean before applying changes.

### Manual Check
- [x] `python -m ruff check src/dpost_v2 tests/dpost_v2`
- [x] `python -m pytest -q tests/dpost_v2`
- [x] `git status --short`

### Completion Notes
- [x] `ruff` passed with expected docstring-rule compatibility warnings only.
- [x] `pytest` passed (`361 passed in 10.90s`).
- [x] Worktree started clean prior to lane edits.

---

## Section: Public CI Hardening
- Why this matters: keeps required branch checks stable while reducing runner/image drift and improving failure diagnostics.

### Checklist
- [x] Pin `Public CI` runner images to stable labels (`ubuntu-24.04`, `windows-2022`).
- [x] Add pip retry/timeout options to reduce transient dependency-install failures.
- [x] Emit JUnit reports for V2 pytest jobs and upload artifacts with `if: always()`.

### Manual Check
- [x] Review `.github/workflows/public-ci.yml` for unchanged job names.
- [x] Verify setup-python uses pip cache plus `cache-dependency-path: pyproject.toml`.
- [x] Verify `unit-tests`, `integration-tests`, and `bootstrap-smoke` publish XML reports.

### Completion Notes
- [x] Existing job names were preserved (`workflow-lint`, `quality`, `unit-tests`, `integration-tests`, `bootstrap-smoke`, `package-build`, `artifact-hygiene`).
- [x] Pytest command lines now include `-ra` and `--junitxml` for better CI signal.
- [x] Package build now uploads build outputs to support post-failure inspection.

---

## Section: Rewrite CI Hardening
- Why this matters: keeps rewrite-lane CI feedback deterministic and rich without changing required-check contract for active branches.

### Checklist
- [x] Pin rewrite workflow runner image to `ubuntu-24.04`.
- [x] Add pip retry/timeout options across V2 quality/test/integration jobs.
- [x] Emit and upload JUnit reports for rewrite V2 tests/integration jobs.

### Manual Check
- [x] Review `.github/workflows/rewrite-ci.yml` for unchanged job names.
- [x] Verify trunk-only integration gate condition remains unchanged.
- [x] Verify rewrite pytest jobs now produce JUnit report artifacts.

### Completion Notes
- [x] Existing rewrite job names were preserved (`rewrite-workflow-lint`, `rewrite-artifact-hygiene`, `rewrite-v2-quality`, `rewrite-v2-tests`, `rewrite-v2-integration`).
- [x] Existing `v2-integration` branch/event guard expression was kept intact.
- [x] New artifacts make flaky-test investigation faster without adding brittle `if` expressions.

---

## Section: Lane Closeout
- Why this matters: records what was validated locally and what still requires GitHub-hosted confirmation.

### Checklist
- [x] Capture stabilization-wave CI status and risks in docs.
- [x] Run lane validation commands after edits.
- [x] Prepare lane handoff summary.

### Manual Check
- [x] `python -m ruff check src/dpost_v2 tests/dpost_v2`
- [x] `python -m pytest -q tests/dpost_v2`
- [x] `git diff -- .github/workflows docs/checklists docs/reports`
- [x] `git status --short`

### Completion Notes
- [x] Local V2 lint/test checks remain green after workflow/docs changes.
- [x] GitHub-hosted runtime/queue behavior remains to be confirmed by actual Actions runs.
- [x] No product runtime code was touched in this lane.
