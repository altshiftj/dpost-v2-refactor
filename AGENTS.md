# AI Agent Instructions (ipat_watchdog -> dpost)

## Purpose
- This repository is migrating from `ipat_watchdog` to `dpost`.
- Keep changes safe, incremental, and reviewable.
- Preserve behavior first; tighten architecture in controlled phases.

## Current Migration Decisions (Locked)
- Runtime posture: headless-first.
- Sync architecture: optional adapters to support multiple databases/ELNs.
- Architecture governance: baseline + contract + responsibility catalog + ADR workflow.

## Scope
- Prefer edits under `src/`, `tests/`, and `docs/`.
- Avoid touching `.venv/`, lockfiles, build artifacts, or generated files unless asked.

## Execution Rules
- Inspect existing code and active architecture docs before editing.
- Use small, targeted diffs that fit the current migration phase.
- Prefer `python -m ...` invocations to avoid PATH issues on Windows.
- Avoid compatibility shims unless explicitly requested or clearly required for transition safety.
- Keep test intent isolated:
- place `ipat_watchdog` contract tests in legacy paths (`tests/unit`, `tests/integration`, `tests/manual`)
- place new `dpost` migration/cutover tests in `tests/migration`

## Human-in-the-loop TDD (Novel Code)
- For new behavior or non-trivial architectural changes:
- First add failing tests and report.
- Wait for human approval.
- Implement until tests pass.
- Human verifies.
- Propose refactors after green.

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
- Tests: `python -m pytest`
- Legacy tests only: `python -m pytest -m legacy`
- Migration tests only: `python -m pytest -m migration`

## Key Paths (Current)
- CLI entrypoint: `src/ipat_watchdog/__main__.py`
- New CLI entrypoint scaffold: `src/dpost/__main__.py`
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
