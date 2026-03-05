# Report: Stabilization CI Reliability Wave

## Title
- Improve V2 CI reliability and diagnostics for `ruff + pytest` during stabilization.

## Date
- 2026-03-05

## Context
- Lane `stabilization-ci-reliability` targets CI reliability and signal quality for active V2 paths (`src/dpost_v2`, `tests/dpost_v2`).
- Scope was restricted to `.github/workflows/**`, `docs/checklists/**`, and `docs/reports/**`.
- Required-check semantics had to remain stable for active branches.

## Findings
- Public and rewrite workflows were using moving runner labels (`ubuntu-latest`, `windows-latest`), which can introduce environmental drift.
- Dependency install steps had no retry/timeout tuning, increasing susceptibility to transient package-index/network failures.
- Pytest jobs reported pass/fail but did not persist structured test reports, reducing post-failure diagnostic quality.
- Existing job names were already aligned to required-check semantics and were preserved unchanged.

## CI Behavior Changes
- Pinned workflow runners to stable images:
  - Public CI: `ubuntu-24.04` and `windows-2022`
  - Rewrite CI: `ubuntu-24.04`
- Added pip resilience options in install steps:
  - `--retries 5 --timeout 60`
- Kept pip cache enabled and added `cache-dependency-path: pyproject.toml` for Python setup.
- Added JUnit generation + artifact upload (`if: always()`) for:
  - `unit-tests`, `integration-tests`, `bootstrap-smoke` in `public-ci.yml`
  - `rewrite-v2-tests`, `rewrite-v2-integration` in `rewrite-ci.yml`
- Added package build artifact upload in Public CI for post-run inspection.

## Evidence
- Workflow edits:
  - `.github/workflows/public-ci.yml`
  - `.github/workflows/rewrite-ci.yml`
- Local validation commands:
  - `python -m ruff check src/dpost_v2 tests/dpost_v2` -> `All checks passed!`
  - `python -m pytest -q tests/dpost_v2` -> `361 passed in 10.90s`
  - `git diff -- .github/workflows docs/checklists docs/reports` (expected lane-scoped changes only)

## Risks
- Runner pinning improves determinism but may require periodic manual upgrades when GitHub deprecates images.
- Artifact upload uses `if-no-files-found: warn`; in hard-fail pre-test scenarios, report artifacts may be missing.
- No hosted GitHub Actions execution was performed from this workspace, so queue/runtime behavior and artifact retention should be verified in a real run.

## Open Questions
- Should integration target discovery move from explicit file lists to marker-based selection for lower maintenance?
  - Answer: Deferred for a later lane; explicit target lists remain intentional during stabilization.
- Should package-build artifacts become required release inputs or stay CI-debug only?
  - Answer: Currently CI-debug only; release handling remains unchanged in this lane.
