# AI Agent Instructions (ipat_watchdog -> dpost)

## Purpose
- This repository is migrating from `ipat_watchdog` to `dpost`.
- Keep changes safe, incremental, and reviewable.
- Preserve behavior first; tighten architecture in controlled phases.
- Active implementation scope is Phase 9+ (post-Phase 8 cutover/retirement).

## Phase 9-13 Operating Mode
- All migration execution guidance in this document is for Phase 9 and later.
- Current objective is native `dpost` runtime completion and legacy runtime
  dependency retirement through Phase 9-13 gates.
- Autonomous execution is default: analyze, test red, implement green, refactor,
  validate, and document in one continuous loop.
- Only pause for human intervention when requirements are ambiguous,
  contradictory, or unsafe.
- Do not introduce human-in-the-loop wait points inside normal TDD cycles.
- Default to bold, subsystem-oriented migration slices when requirements are
  clear.
- Prefer meaningful retirement checkpoints over micro-edits (for example an
  entire harness seam, runtime seam, or plugin family seam).
- Keep changes reviewable, but do not split tightly coupled edits into separate
  commits solely for caution.
- During implementation, use focused tests for fast feedback; run required
  full gates once per checkpoint before commit.
- Avoid repetitive full-suite reruns mid-slice unless failure signals broad
  regression risk.

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
- Use bounded but substantial diffs that fit the current migration phase.
- Prefer grouped vertical slices across tightly coupled capabilities whenever
  that accelerates retirement safely:
- processing core rehost
- record lifecycle rehost
- sync core rehost
- config runtime rehost
- shim retirement/import sweep
- Do not split tightly coupled capability updates only to preserve an
  artificially small diff.
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

## Autonomous TDD (Novel Code)
- For Phase 9+ behavior changes or non-trivial architectural changes, run full
  TDD loops autonomously:
- add failing tests and capture red-state evidence
- implement until tests pass
- refactor while tests stay green
- report red/green verification evidence and rationale
- maintain a fast cadence: one explicit red-to-green loop per migration slice,
  then run required full gates before checkpoint commit
- Do not pause for human approval between red and green unless requirements are ambiguous or unsafe.

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
- checkpoint scope should be meaningful (subsystem or boundary-level), not
  micro-step commits unless needed to recover from risk
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

## Output Expectations
- Summarize what changed and why.
- Report tests/lint executed, or state clearly if not run.
- When sharing commands, provide full terminal-ready lines.

## Glossary Rules
- Maintain `GLOSSARY.csv` at repository root.
- Columns: `term,type,purpose,usage`.
- Include only project-defined terms (exclude vendor/library terms).
- Add glossary entries when introducing new internal terms in code/docs.
