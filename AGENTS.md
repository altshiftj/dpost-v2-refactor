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

## Refactor-First Playbook (Current Process)
- Primary objective: reduce architectural risk in orchestration-heavy modules while preserving behavior.
- Current validated checkpoint:
  - `python -m pytest -q`
  - `741 passed, 1 skipped, 1 warning`
  - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit`
  - `706 passed, 1 skipped, 1 warning`
  - `100%` total coverage (`5325 stmts, 0 miss`)
  - `python -m ruff check .` -> pass
- Current priority queue (in order):
  1. `src/dpost/application/processing/file_process_manager.py`
     - failure outcome construction vs emission split completed
     - injectable failure emission sink completed (`failure_emitter.py`)
     - immediate-sync error emission sink extraction completed
     - constructor startup-sync side effect removed; explicit startup hook completed
     - post-persist bookkeeping plan/emitter seam completed (`post_persist_bookkeeping.py`)
     - next: continue post-persist side-effect decomposition (record mutation boundaries / record manager update adapter seam)
  2. deep helper global-config access cleanup (`current()/get_service()` reduction)
     - push runtime/config lookup to composition boundaries
     - `filesystem_utils` explicit-context support completed
     - `RecordManager` explicit persisted-record path/id-separator wiring completed
     - processing routing hot path now passes explicit naming context (`filename_pattern`, `id_separator`)
     - file-process persistence hot path now passes explicit naming/storage context (`id_separator`, `dest_dir`, `current_device`)
      - `SessionManager` timeout-provider seam completed
      - Kinexus/PSA lazy separator seams completed
      - `application/naming/policy.py` wrapper explicit-context slice completed
      - failure/exception move path now passes explicit exception context (`exception_dir`, `id_separator`)
      - manual-rename bucket path now passes explicit rename context (`rename_dir`, `id_separator`)
     - next: remaining runtime/storage helper compatibility wrappers (`filesystem_utils`, `naming wrappers`) and composition-root call-site cleanup
  3. retry policy unification across resolver/watchdog processing flows
     - shared retry-delay policy seam completed (`retry_planner`, `device_resolver`, `device_watchdog_app`)
     - stability/result explicit outcome semantics completed in resolver + stability tracker
     - next: centralize runtime retry config wiring if further consolidation is needed
  4. test hygiene automation
     - guard test added (`tests/unit/test_unique_test_module_basenames.py`)
     - import-key collision policy (package-scoped modules allowed to reuse basenames)
     - virtual-time scheduler helper completed (`HeadlessUI(use_virtual_time=True)`, `advance_scheduled_time`)
     - observer-factory integration fixture cleanup completed
     - next: expand delay-aware integration assertions where retry timing matters
- Supporting reference docs:
  - `docs/reports/20260221-coverage-informed-architecture-findings.md`
  - `docs/reports/20260221-coverage-to-refactor-insights-deep-dive.md`
  - `docs/checklists/20260221-coverage-hardening-action-items-checklist.md`
  - `docs/planning/20260221-overnight-refactor-run-roadmap.md`
  - `docs/checklists/20260221-overnight-refactor-execution-checklist.md`

## Efficient Validation and Documentation Standard
- Test enough, not excess:
  - add focused red/green unit tests for changed behavior and extracted seams
  - avoid broad speculative tests that do not protect current/next refactor slice
  - run targeted test files during implementation
  - run full `tests/unit` + coverage only at major checkpoints
- Document enough, not excess:
  - append one concise note per completed slice:
    - intended action
    - expected outcome
    - observed outcome
    - commands run and results
  - avoid long narrative logs for minor intermediate edits
  - when a coverage residual is classified as defensive/unreachable, record the
    rationale at the slice where it is resolved

## Autonomous Execution and Communication Cadence
- Default mode: fully autonomous execution across analysis -> test -> refactor -> validate -> document.
- Keep user in the loop at major section boundaries only:
  - after completing a full refactor slice/module
  - after full checkpoint validation
  - when blocked by ambiguity/unsafe changes
- Do not pause for approval between micro-steps when requirements are clear and safe.

## Overnight Autonomous SOP (Active When Requested)
- Execution posture:
  - run continuously through queued refactor slices without waiting for chat acknowledgment
  - prefer completing full subsystem slices before switching context
  - keep momentum on highest-risk modules until checkpoint gates fail or scope is exhausted
- Communication posture:
  - suppress non-essential progress chatter during active overnight runs
  - report only on:
    - blocker/ambiguity requiring human decision
    - major checkpoint completion
    - end-of-run summary
- Validation cadence:
  - per slice:
    - targeted `ruff` + targeted `pytest`
  - every 2-3 slices (or after risky refactor moves):
    - full `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit`
  - if coverage tool state conflicts:
    - run `python -m coverage erase` and rerun checkpoint
- Documentation cadence:
  - append one concise slice note to active findings report after each completed slice
  - update roadmap/checklist progress at each full checkpoint
  - avoid long-form narrative unless architecture decisions materially change

## Refactor Guardrails
- Preserve external behavior and runtime contracts while restructuring internals.
- Prefer extracting pure functions/classes before changing orchestration flow.
- Keep dependency direction aligned with architecture contract (application -> ports, infrastructure -> adapters).
- Avoid introducing new global singletons or hidden runtime context reads.
- Maintain test hygiene:
  - unique test module basenames in non-package directories
  - deterministic time/thread tests via controllable fakes/stubs
