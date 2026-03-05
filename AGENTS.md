# AI Agent Instructions (dpost)

## Purpose
- Default focus: implement and maintain V2 runtime code/tests under
  `src/dpost_v2/` and `tests/dpost_v2/`.
- Keep work deterministic, reviewable, and checkpointed.
- Keep docs/tooling aligned with active V2 behavior.

## Current Phase (Locked)
- Execution target: V2-only runtime and tests using TDD.
- Canonical artifacts:
  - `docs/architecture/`
  - `docs/checklists/`
  - `docs/reports/`
  - `docs/ops/lane-prompts/`
- Migration-era V1->V2 planning artifacts are historical records unless
  explicitly marked active.

## Operating Mode
- Autonomous execution is default.
- Work in high-coherence sections (contracts, startup, domain, ingestion,
  infrastructure, plugins, runtime, tests, docs/tooling).
- Continue until the assigned lane packet is complete.
- Ask for human input only when hard-blocked (credentials/system outage or
  contradictory instructions).

## Scope
- Prefer edits under `src/dpost_v2/`, `tests/dpost_v2/`, `docs/`, and repo
  tooling/config files requested by the lane.
- Do not edit archived legacy runtime (`src/dpost/`) or archived legacy tests
  unless explicitly requested.
- Do not touch `.venv/`, lockfiles, build artifacts, or generated files.

## TDD Rules (Mandatory)
For each implementation slice:
1. Write or update failing tests first.
2. Implement minimal code to pass tests.
3. Refactor with tests green.
4. Keep layering contracts intact.

A slice is incomplete if:
- behavior changed without test updates,
- tests are nondeterministic,
- layering constraints are violated.

## Execution Workflow
1. Align target behavior with active architecture/docs.
2. Add failing tests in `tests/dpost_v2/`.
3. Implement minimal code in `src/dpost_v2/`.
4. Refactor for clarity with tests green.
5. Validate lane-targeted checks.
6. Commit lane-complete checkpoints.

## Checkpoint and Commit Protocol
- Commit by completed behavior slice.
- Suggested style: `v2: <lane> <behavior-slice>`.
- Do not wait for extra approval for routine lane-scoped edits.

## Planning and Tracking
- Use `docs/checklists/` for execution state.
- Use `docs/reports/` for implementation findings and risk notes.
- Use `docs/planning/` only for active architecture/scope plans.

Checklist entries should include:
- `Why this matters`
- `Manual Check`
- `Completion Notes`

## Layering Constraints
- `domain`: pure business/data semantics
- `application`: orchestration and contracts
- `infrastructure`: side-effect adapters
- `plugins`: extension points
- `runtime`: composition/startup

Do not mix infrastructure behavior into domain/application modules.

## Commands
- Validation:
  - `python -m ruff check src/dpost_v2 tests/dpost_v2`
  - `python -m pytest -q tests/dpost_v2`
  - `git status`
  - `git diff`
- Optional quality gate:
  - `python -m pre_commit run --all-files`

## Git Safety Rules
- Allowed:
  - `git add ...`
  - `git commit ...`
- Allowed read-only:
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

## Glossary Rules
- If new internal terms are introduced, update `GLOSSARY.csv`.
- Required columns: `term,type,purpose,usage`.

## Output Expectations
At section completion, report:
- files modified,
- checks run,
- blocked/deferred items.

## Overnight Autonomous SOP (When Requested)
- Execute assigned sections continuously with minimal interruption.
- Post updates at section boundaries and blockers.
- End with concise handoff and exact next file.
