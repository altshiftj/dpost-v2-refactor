# Report: OSS Readiness Gap Assessment (Post-CI Baseline)

## Date
- 2026-03-03

## Scope
- Assess remaining codebase/repository changes needed for a robust open-source posture after environment hygiene and public CI baseline work.

## Baseline Already In Place
- MIT license present (`LICENSE`).
- Governance baseline present (`README`, `CONTRIBUTING`, `SECURITY`, `CODE_OF_CONDUCT`).
- Public CI workflow present (`.github/workflows/public-ci.yml`) with lint, tests, bootstrap smoke, package build, and artifact hygiene checks.
- Branch-protection mapping is codified in-repo (`.github/branch-protection/main.required-checks.json`) with an apply script (`scripts/github/set-main-branch-protection.ps1`).

## Changes Applied In This Pass
- Made Windows-only dependencies platform-conditional in `pyproject.toml`:
  - `pywin32; sys_platform == 'win32'`
  - `pywin32-ctypes; sys_platform == 'win32'`
- Replaced machine-local absolute links (`/d:/Repos/...`) in active CI docs with repository-relative links.
- Aligned quality-gate command examples in contributor docs with current CI behavior.

## Remaining Gaps (Prioritized)

### P0: Required Before Public Enforcement
- Canonical forge mismatch for enforcement:
  - Current `origin` is GitLab, while branch-protection automation added so far targets GitHub API.
  - Required action: either migrate canonical remote to GitHub and apply current payload, or add equivalent GitLab protected-branch automation.
- Test-surface stratification:
  - `tests/manual/` still lives under pytest discovery with `test_*.py` naming.
  - Required action: mark manual tests explicitly (for example `@pytest.mark.manual`) and exclude from default CI target; run them only in explicit/manual jobs.

### P1: Strongly Recommended Early
- Add OSS collaboration templates:
  - `.github/ISSUE_TEMPLATE/*`
  - `.github/pull_request_template.md`
- Add dependency maintenance automation:
  - Dependabot/Renovate config for GitHub Actions + Python dependencies.
- Add release automation:
  - tag-driven build/release workflow with artifact publication policy.
- Harden CI supply-chain posture:
  - pin third-party GitHub Actions to full commit SHA, not moving tags.

### P2: Quality Improvements
- Expand package metadata in `pyproject.toml` (classifiers, project URLs) for better PyPI/OSS discoverability.
- Add explicit maintainer/reviewer ownership files (`CODEOWNERS`) once team ownership is stable.

## Validation Evidence
- Packaging marker update confirmed in `pyproject.toml`.
- No active `/d:/Repos/...` links remain in active, non-archive docs from this CI slice.
- Bootstrap smoke subset still passes:
  - `python -m pytest -q tests/unit/runtime/test_bootstrap.py tests/unit/runtime/test_bootstrap_additional.py`
  - Result: `17 passed`.
