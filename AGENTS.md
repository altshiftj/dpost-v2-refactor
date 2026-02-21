# AI Agent Instructions (dpost)

## Purpose
- Maintain `dpost` as the single canonical runtime and extension surface.
- Keep changes safe, reviewable, and architecture-aligned.
- Preserve behavior first; improve structure with clear ownership boundaries.

## Operating Mode
- Autonomous execution is default: analyze, red test, green implementation,
  refactor, validate, and document in one continuous loop.
- Only pause for human intervention when requirements are ambiguous,
  contradictory, or unsafe.
- Prefer subsystem-level slices over micro-edits when requirements are clear.
- Run focused tests during implementation; run full gates at checkpoints.

## Current Decisions (Locked)
- Runtime posture: headless-first with optional desktop mode.
- Sequencing posture: framework-first (contracts and composition before
  concrete integrations).
- Sync architecture: adapter-based with optional backends.
- Governance posture: baseline + contract + responsibility catalog + ADRs.

## Scope
- Prefer edits under `src/`, `tests/`, and `docs/`.
- Avoid touching `.venv/`, lockfiles, build artifacts, or generated files
  unless asked.

## Execution Rules
- Inspect code and architecture docs before editing.
- Prefer bounded, meaningful diffs grouped by ownership boundaries.
- Prefer `python -m ...` commands on Windows.
- Avoid compatibility wrappers unless explicitly requested.
- Keep test intent explicit:
  - `tests/unit`, `tests/integration`, and `tests/manual` for canonical
    behavior and boundary coverage
  - `legacy` marker only for archived compatibility characterization suites

## Import Policy
- `src/dpost/**` must not add direct `ipat_watchdog.*` imports.
- Any exception requires explicit human approval and architecture notes.

## Autonomous TDD
- For non-trivial behavior or architecture changes:
  - add failing tests and capture red-state evidence
  - implement to green
  - refactor with tests green
  - report red/green evidence and rationale
- Do not pause between red and green unless requirements are ambiguous or unsafe.

## Architecture Governance (Required)
- Source-of-truth artifacts:
  - `docs/architecture/architecture-baseline.md`
  - `docs/architecture/architecture-contract.md`
  - `docs/architecture/responsibility-catalog.md`
  - `docs/architecture/adr/`
- Keep them updated for architecture-impacting changes.
- Record major decisions as ADRs.
- Keep terminology aligned with `GLOSSARY.csv`.

## Planning and Tracking
- Use:
  - `docs/reports/` for findings
  - `docs/planning/` for approach
  - `docs/checklists/` for execution steps
- Move historical sets to:
  - `docs/reports/archive/`
  - `docs/planning/archive/`
  - `docs/checklists/archive/`
  - `docs/refactors/archive/`
- Checklists must include:
  - short `Why this matters` blurbs per section
  - final `Manual Check` with concrete validation steps
  - completion notes (`How it was done`)

## Layering Constraints
- Follow the architecture contract:
  - domain: pure business/data rules
  - application: orchestration and ports
  - infrastructure: adapters and external integrations
  - plugins: device/PC extensions
- Keep dependency wiring in composition root boundaries.
- Do not introduce new global singletons without explicit approval.
- Application code should depend on ports, not concrete adapters.

## Code Style
- Python 3.12+.
- Format with Black (88 columns).
- Lint with Ruff.
- Keep strict typing discipline; avoid shortcuts unless justified.
- Add type hints for new public functions.
- Add docstrings for new tests and functions.

## Commands
- Lint: `python -m ruff check .`
- Lint fix: `python -m ruff check . --fix`
- Format: `python -m black .`
- Pre-commit: `python -m pre_commit run --all-files`
- Tests: `python -m pytest`
- Legacy tests only: `python -m pytest -m legacy`

## Git Safety Rules
- Primary goal: prevent destructive operations during autonomous execution.
- Checkpoint commit policy (`experiment/autonomous-tdd`):
  - stage all current checkpoint work with `git add .`
  - create normal commits with clear scope/result messages
  - do not wait for extra approval unless requirements become ambiguous/unsafe
- Allowed git write operations:
  - `git add ...`
  - `git commit ...`
- Allowed quality gate command:
  - `python -m pre_commit run --all-files`
- Allowed git read operations:
  - `git status`
  - `git diff`
  - `git log`
- Forbidden unless explicitly requested:
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
- Share terminal-ready commands when listing commands.

## Glossary Rules
- Maintain `GLOSSARY.csv` at repository root.
- Columns: `term,type,purpose,usage`.
- Include only project-defined terms (exclude vendor/library terms).
- Add entries when introducing new internal terms.

## Coverage Hardening Playbook (Current Process)
- Primary objective: raise `tests/unit` coverage for `src/dpost/**` while preserving behavior.
- Target posture:
  - prioritize branch and error/fallback paths, not just happy-path line execution
  - prefer low-risk, high-yield modules first, then orchestration-heavy modules
  - keep production code changes separate from test-only coverage work unless explicitly requested
- Execution loop:
  1. take baseline:
     - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit`
  2. pick next slice from highest missed lines with manageable test seams
  3. add focused unit tests (red/green) for selected branches
  4. validate slice:
     - `python -m ruff check tests/unit`
     - `python -m pytest -q <targeted test paths>`
  5. run checkpoint baseline again and update docs
- Current coverage governance artifacts:
  - findings report:
    - `docs/reports/20260221-coverage-informed-architecture-findings.md`
  - execution/action checklist:
    - `docs/checklists/20260221-coverage-hardening-action-items-checklist.md`
- Documentation requirement per checkpoint:
  - record exact commands executed
  - record pass/fail outcomes and known warnings
  - record top uncovered modules and next planned slice
  - maintain lightweight in-flight notes for each slice:
    - intended action (what we are about to change/test)
    - expected outcome (what should improve or be validated)
    - observed outcome (what actually happened, including blockers)
  - keep notes concise and append-only so progress is easy to audit
- Priority modules for deeper follow-up refactoring/testing:
  - `src/dpost/application/processing/file_process_manager.py`
  - `src/dpost/application/processing/stability_tracker.py`
  - `src/dpost/application/runtime/device_watchdog_app.py`
  - `src/dpost/infrastructure/sync/kadi_manager.py`
  - `src/dpost/plugins/system.py`
- Test hygiene rules for this process:
  - keep test module basenames unique across non-package test directories
  - avoid introducing flaky time/thread dependencies without controllable clocks/events
  - do not rely on global active config in tests unless explicitly validating that behavior
