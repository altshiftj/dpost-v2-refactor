# Checklist: OSS Readiness Hardening (Post-Public-CI)

## Objective
- Close remaining codebase and repository gaps so the project can operate as a stable, contributor-friendly OSS repository.

## Section 1: Launch-Critical
- Why this matters: These items directly affect whether governance and CI enforcement are real, not just documented.
- [ ] Decide canonical forge for enforcement (`GitHub` vs `GitLab`) and make branch protection mandatory on that host.
- [ ] If canonical host remains GitLab, add host-native protected-branch automation and required pipeline checks.
- [ ] Mark `tests/manual/**` as explicit manual tests and exclude them from default CI execution.
- [ ] Split CI test execution into explicit lanes (`unit`, optional `integration`, optional `manual`) with clear required/optional status.

## Section 2: Early OSS Hygiene
- Why this matters: These changes reduce maintainer toil and make contribution flow self-serve.
- [x] Make Windows-only runtime dependencies platform-conditional in `pyproject.toml`.
- [x] Replace machine-local absolute links in active docs with repository-relative links.
- [ ] Add issue templates under `.github/ISSUE_TEMPLATE/`.
- [ ] Add `.github/pull_request_template.md` with test/doc checklist.
- [ ] Add dependency update automation (`dependabot.yml` or Renovate config).
- [ ] Pin third-party GitHub Actions to full SHA for supply-chain hygiene.

## Section 3: Publishing/Metadata
- Why this matters: Better metadata and release mechanics reduce friction for external users and package consumers.
- [ ] Add `project.urls` and package classifiers to `pyproject.toml`.
- [ ] Add release workflow (tag-triggered build + release artifact policy).
- [ ] Add `CODEOWNERS` once long-term module ownership is finalized.

## Completion Notes
- How it was done:
  - Audited repository against OSS baseline expectations after CI/environment hygiene passes.
  - Applied low-risk/high-impact fixes immediately (platform markers and portable links).
  - Captured unresolved items as actionable host/test/governance backlog.

## Manual Check
- Verify no local absolute links in active docs:
  - `rg -n "/d:/Repos|/c:/|/C:/|/D:/" docs README.md CONTRIBUTING.md DEVELOPER_README.md USER_README.md --glob '!docs/**/archive/**'`
- Verify Windows-only deps are platform-conditional:
  - `rg -n "pywin32|pywin32-ctypes" pyproject.toml`
- Verify bootstrap smoke remains green:
  - `python -m pytest -q tests/unit/runtime/test_bootstrap.py tests/unit/runtime/test_bootstrap_additional.py`
