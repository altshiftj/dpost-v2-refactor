# AI Agent Instructions (ipat_watchdog -> dpost)

## Purpose
- This repository is migrating from `ipat_watchdog` to `dpost`.
- Keep changes safe, incremental, and reviewable.
- Preserve behavior first; tighten architecture in controlled phases.
- Active implementation scope is Phase 9+ (post-Phase 8 cutover/retirement).

## Active Phase Scope (Phase 9+)
- All migration execution guidance in this document is for Phase 9 and later.
- Prior phase notes remain historical context unless explicitly reactivated.
- Current objective is native `dpost` runtime completion and legacy runtime
  dependency retirement through Phase 9-13 gates.
- Autonomy posture for Phase 9-13 is fully autonomous execution by default:
  plan, test, implement, refactor, validate, and document without waiting for
  step-by-step human approvals.

## Phase 9-13 Full Autonomy Mandate
- For all work scoped to Phases 9 through 13, treat autonomous execution as the
  default operating mode.
- Execute end-to-end within a single session whenever feasible:
- analyze architecture context
- run tests-first red-state setup
- implement to green
- refactor with tests green
- update required architecture/reporting artifacts
- report outcomes and remaining risks
- Only pause for human intervention when requirements are ambiguous,
  contradictory, or unsafe.
- Do not introduce human-in-the-loop wait points inside normal TDD cycles for
  Phase 9-13 execution.

## Current Migration Decisions (Locked)
- Runtime posture: headless-first.
- Migration sequencing: framework-first (kernel/contracts/reference implementations before concrete integrations).
- Sync architecture: optional adapters to support multiple databases/ELNs.
- Architecture governance: baseline + contract + responsibility catalog + ADR workflow.

## Scope
- Prefer edits under `src/`, `tests/`, and `docs/`.
- Avoid touching `.venv/`, lockfiles, build artifacts, or generated files unless asked.

## Execution Rules
- Inspect existing code and active architecture docs before editing.
- Use small, targeted diffs that fit the current migration phase.
- Keep implementation scope to one capability slice per change set whenever
  feasible:
- processing core rehost
- record lifecycle rehost
- sync core rehost
- config runtime rehost
- shim retirement/import sweep
- Do not combine multiple capability slices in one implementation change unless
  the extra scope is documentation-only synchronization.
- Prefer `python -m ...` invocations to avoid PATH issues on Windows.
- Avoid compatibility shims unless explicitly requested or clearly required for transition safety.
- Apply framework-first sequencing:
- define and test framework contracts and composition paths first
- add reference implementations second (for example test plugin, noop adapter)
- migrate concrete plugins/adapters only after framework gates are green
- Keep test intent isolated:
- place `ipat_watchdog` contract tests in legacy paths (`tests/unit`, `tests/integration`, `tests/manual`)
- place new `dpost` migration/cutover tests in `tests/migration`

## Legacy Import Policy (Phase 9-13)
- Legacy imports in `src/dpost/**` are retired.
- No `src/dpost/**` module may add direct `ipat_watchdog.*` imports without
  explicit human approval and documentation rationale in active migration
  reports/checklists.

## Shim Retirement Exit Criteria (Required)
- Status (2026-02-21): criteria satisfied and both shim modules are retired.
- `src/dpost/application/runtime/runtime_dependencies.py` may be retired only
  when all are true:
- runtime app and processing ownership paths resolve through dpost-owned modules
  (`dpost.application.processing`, `dpost.application.records`,
  `dpost.application.session`, `dpost.application.config`,
  `dpost.application.metrics`)
- no direct `ipat_watchdog.core.*` imports remain in canonical runtime/app
  ownership paths (`src/dpost/application/runtime/`,
  `src/dpost/application/processing/`)
- migration contracts for runtime app rehost/boundaries are green
  (`tests/migration/test_phase10_runtime_app_rehost.py` and
  `tests/migration/test_phase13_legacy_runtime_retirement.py`)
- required global gates are green (`python -m pytest -m migration`,
  `python -m ruff check .`, `python -m black --check .`, `python -m pytest`)
- `src/dpost/infrastructure/runtime/config_dependencies.py` may be retired only
  when all are true:
- runtime bootstrap config/storage wiring resolves through native dpost modules
  (not legacy-backed boundary wrappers)
- no direct `ipat_watchdog.core.config*` or
  `ipat_watchdog.core.storage.filesystem_utils` imports remain under
  `src/dpost/infrastructure/runtime/` except approved UI boundary paths
- migration contracts for runtime infrastructure boundaries are green
  (`tests/migration/test_phase11_runtime_infrastructure_boundary.py` and
  `tests/migration/test_phase13_legacy_runtime_retirement.py`)
- required global gates are green (`python -m pytest -m migration`,
  `python -m ruff check .`, `python -m black --check .`, `python -m pytest`)

## Autonomous TDD (Novel Code)
- For Phase 9+ behavior changes or non-trivial architectural changes, run full
  TDD loops autonomously:
- add failing tests and capture red-state evidence
- implement until tests pass
- refactor while tests stay green
- report red/green verification evidence and rationale
- Do not pause for human approval between red and green unless requirements are ambiguous or unsafe.

## Reasoning Effort Policy
- Very high reasoning effort:
- documentation analysis/updates (architecture, planning, checklists, ADR impact)
- test design and test writing
- code design, implementation, and refactoring
- Medium reasoning effort:
- running test/lint/format/pre-commit commands
- git status/review and commit workflow operations

## Architecture Governance (Required)
- Treat these as source-of-truth artifacts:
- `docs/architecture/architecture-baseline.md`
- `docs/architecture/architecture-contract.md`
- `docs/architecture/responsibility-catalog.md`
- `docs/architecture/adr/`
- Keep them updated when architecture-impacting changes are made.
- Record major decisions as ADRs.
- Keep terminology aligned with `GLOSSARY.csv`.

## Planning and Tracking Workflow
- Use RPC documentation for substantial work:
- `docs/reports/` for findings
- `docs/planning/` for approach
- `docs/checklists/` for execution steps
- Keep active migration docs at each folder root and move historical sets to matching archive folders:
- `docs/reports/archive/`
- `docs/planning/archive/`
- `docs/checklists/archive/`
- `docs/refactors/archive/`
- Checklists must include:
- a short `Why this matters` blurb per section
- a final `Manual Check` section with concrete human validation steps
- completion notes (`How it was done`) when sections are finished

## Layering and Design Constraints
- Follow the architecture contract:
- domain: pure business/data rules
- application: orchestration and ports
- infrastructure: adapters and external integrations
- plugins: device/PC extensions
- Keep dependency wiring in a composition root.
- Do not introduce new global singletons without explicit approval.
- Application code should depend on sync ports, not concrete backend adapters.

## Code Style
- Python 3.12+.
- Format with Black (88 columns).
- Lint with Ruff.
- Maintain strict typing discipline; avoid shortcuts unless justified.
- Add type hints for new public functions.
- Add docstrings for new tests and functions.

## Commands
- Lint: `python -m ruff check .`
- Lint fix: `python -m ruff check . --fix`
- Format: `python -m black .`
- Pre-commit: `python -m pre_commit run --all-files`
- Tests: `python -m pytest`
- Legacy tests only: `python -m pytest -m legacy`
- Migration tests only: `python -m pytest -m migration`

## Git Safety Rules
- Primary goal: prevent destructive repository operations during autonomous execution.
- Checkpoint commit policy (experiment/autonomous-tdd):
- at major autonomous checkpoints, stage all current migration work with
  `git add .` and create a normal commit with a clear scope/result message
  before continuing further slices
- do not wait for extra human approval to create these checkpoint commits
  unless requirements become ambiguous or unsafe
- Allowed git write operations:
- `git add ...`
- `git commit ...`
- Allowed quality gate command:
- `python -m pre_commit run --all-files`
- Allowed git read operations:
- `git status`
- `git diff`
- `git log`
- Forbidden git operations unless explicitly requested by a human:
- `git reset --hard`
- `git checkout -- ...`
- `git clean -fd` / `git clean -fdx`
- `git rebase`
- `git merge`
- `git cherry-pick`
- `git commit --amend`
- `git push --force`

## Key Paths (Current)
- Canonical CLI entrypoint: `src/dpost/__main__.py`
- Legacy CLI entrypoint (retired): `src/ipat_watchdog/__main__.py`
- Runtime bootstrap: `src/ipat_watchdog/core/app/bootstrap.py`
- New composition root scaffold: `src/dpost/runtime/composition.py`
- Architecture docs: `docs/architecture/`
- Migration plan/checklist: `docs/planning/20260218-dpost-architecture-tightening-plan.md`, `docs/checklists/20260218-dpost-architecture-tightening-checklist.md`
- Migration tests: `tests/migration/`

## Output Expectations
- Summarize what changed and why.
- Report tests/lint executed, or state clearly if not run.
- When sharing commands, provide full terminal-ready lines.

## Glossary Rules
- Maintain `GLOSSARY.csv` at repository root.
- Columns: `term,type,purpose,usage`.
- Include only project-defined terms (exclude vendor/library terms).
- Add glossary entries when introducing new internal terms in code/docs.
