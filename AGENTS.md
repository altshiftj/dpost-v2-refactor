# AI Agent Instructions (dpost)

## Purpose
- Build `dpost` V2 as a cleanroom, OSS-ready architecture with explicit contracts.
- Treat V1 as reference input, not as the design authority for new code.
- Optimize for clarity, contributor onboarding, and safe incremental delivery.

## Current Phase (Locked)
- Repository of record: `D:\Repos\d-post`.
- Canonical planning docs:
  - `docs/planning/20260303-v2-cleanroom-rewrite-blueprint-rpc.md`
  - `docs/planning/20260303-v1-to-v2-exhaustive-file-mapping-rpc.md`
- Canonical pseudocode tree: `docs/pseudocode/` (no `docs/pseudocode/v2`).
- Primary implementation target: `src/dpost_v2/`.
- V1 runtime (`src/dpost/`) is maintenance-only unless explicitly requested.

## Operating Mode
- Autonomous execution is default: analyze, red test, green implementation, refactor, validate, document.
- Do not pause for micro-approvals unless requirements are ambiguous, contradictory, or unsafe.
- Work in subsystem slices with clear ownership boundaries.

## Scope
- Prefer edits under:
  - `docs/pseudocode/`
  - `docs/planning/`
  - `docs/checklists/`
  - `docs/reports/`
  - `src/dpost_v2/`
  - `tests/` (V2-focused coverage)
- Avoid touching `.venv/`, lockfiles, generated artifacts, and unrelated legacy files unless asked.

## Execution Workflow (V2)
1. Align contract intent in planning docs and pseudocode docs.
2. Add or update focused failing tests for the current slice.
3. Implement minimal V2 code to pass tests.
4. Refactor for readability and boundary clarity with tests still green.
5. Run targeted checks, then periodic full checkpoints.
6. Record concise slice notes in checklist/report artifacts.

## Layering Constraints
- Domain: pure business/data rules with no infrastructure dependencies.
- Application: orchestration, use-cases, and port contracts only.
- Infrastructure: adapter implementations and external integrations.
- Plugins: extension points for device/PC behavior.
- Composition wiring belongs at runtime/composition boundaries.
- Do not introduce new global singletons without explicit approval.

## Import Policy
- `src/dpost_v2/**` must not import `ipat_watchdog.*`.
- `src/dpost_v2/**` must not depend directly on `src/dpost/**` runtime internals.
- Any exception requires explicit human approval plus architecture notes.

## Cleanroom Guardrails
- No compatibility wrapper carryover by default.
- No ambient config lookups in deep helpers.
- No hidden side effects in constructors.
- Prefer explicit context objects and port interfaces.

## Testing Standard
- TDD for non-trivial behavior and architecture slices:
  - capture red-state evidence
  - implement to green
  - refactor with green tests
- Use focused unit tests during slices; run broader gates at checkpoints.
- Keep test intent explicit and deterministic.

## Documentation Standard
- Pseudocode docs in `docs/pseudocode/` are the executable design contract.
- Keep blueprint/mapping docs synchronized with actual structure.
- Checklists must include:
  - brief `Why this matters`
  - completion note (`How it was done`)
  - `Manual Check` validation steps

## Code Style
- Python 3.12+.
- Format with Black (88 columns).
- Lint with Ruff.
- Keep strict typing discipline.
- Add type hints for public functions.
- Add concise docstrings for new tests and new public functions.

## Commands
- Lint: `python -m ruff check .`
- Lint fix: `python -m ruff check . --fix`
- Format: `python -m black .`
- Pre-commit: `python -m pre_commit run --all-files`
- Tests: `python -m pytest`

## Git Safety Rules
- Primary goal: prevent destructive operations during autonomous execution.
- Allowed git write operations:
  - `git add ...`
  - `git commit ...`
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
- Report tests/lint run, or clearly state if not run.
- Provide terminal-ready commands when listing commands.

## Glossary Rules
- Maintain `GLOSSARY.csv` at repo root.
- Columns: `term,type,purpose,usage`.
- Add entries when introducing project-defined terms.
