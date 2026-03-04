# AI Agent Instructions (dpost)

## Purpose
- Task focus (current run): implement V2 runtime code and tests in `src/dpost_v2/` and `tests/dpost_v2/`.
- Preserve traceability to pseudocode and migration mapping so parallel lanes do not drift.
- Keep work reviewable, deterministic, and checkpointed.

## Current Phase (Locked)
- Execution target: V2 implementation and tests using TDD.
- Canonical artifacts:
  - `docs/planning/20260303-v2-cleanroom-rewrite-blueprint-rpc.md`
  - `docs/planning/20260303-v1-to-v2-exhaustive-file-mapping-rpc.md`
  - `docs/pseudocode/`
  - `docs/ops/lane-prompts/`
- Documentation refinement is in scope only when needed to maintain implementation traceability.

## Operating Mode
- Autonomous execution is default.
- Work in discrete, high-coherence sections (contracts, startup, domain, ingestion, infrastructure, plugins, runtime, tests).
- Continue until the user issues a stop or the assigned lane packet is complete.
- Only ask for human input when ambiguity threatens correctness.

## Scope
- Prefer edits under `src/dpost_v2/`, `tests/dpost_v2/`, `docs/ops/lane-prompts/`, `docs/checklists/`, `docs/planning/`, and `docs/reports/`.
- Do not edit legacy `src/dpost/` or legacy tests unless explicitly requested.
- Do not touch `.venv/`, lockfiles, build artifacts, or generated files.

## TDD Rules (Mandatory)
For each implementation slice:
1. Write or update failing tests first.
2. Implement minimal code to pass tests.
3. Refactor while keeping tests green.
4. Keep changes lane-scoped and contract-safe.

A slice is incomplete if:
- behavior changed but tests were not added/updated,
- tests are not deterministic,
- layering constraints are violated.

## Execution Workflow for This Task
1. Map/align
   - Align implementation target to pseudocode and V1 mapping.
2. Test-first
   - Add failing tests in `tests/dpost_v2/` for the target behavior.
3. Implement
   - Add minimal code in `src/dpost_v2/` to satisfy tests.
4. Refactor
   - Improve clarity/structure with tests still passing.
5. Validate
   - Run lane-targeted lint/tests and reconcile failures.
6. Commit
   - Commit lane-complete checkpoints with scoped messages.

## Checkpoint and Commit Protocol
- Commit frequently by completed lane slice, not as one giant pass.
- Suggested commit style: `v2: <lane> <behavior-slice>`.
- Do not wait for extra approvals for routine lane-scoped edits.

## Planning and Tracking
- Use `docs/checklists/` for execution order and completion state.
- Use `docs/reports/` for summary risk/quality notes.
- Use `docs/planning/` for architecture/scope changes.
- Keep checklists with:
  - `Why this matters`
  - `Manual Check`
  - `Completion Notes`

## Layering Constraints
- Preserve V2 layer boundaries:
  - domain: pure business and data semantics
  - application: orchestration, contracts, orchestrators
  - infrastructure: adapters and side effects
  - plugins: extension points
  - runtime: composition and startup
- Do not mix infrastructure behavior into domain/application.
- Keep contracts explicit and stable across lanes.

## Commands
- Implementation validation:
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
- Allowed read only:
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
- If new internal terms are introduced in implementation/planning docs, add/update entries in `GLOSSARY.csv` at repo root.
- Required columns: `term,type,purpose,usage`.

## Output Expectations
- At section completion, report:
  - files modified,
  - checks run,
  - any blocked or deferred items.

## Overnight Autonomous SOP (When Requested)
- Execute all assigned sections continuously in order with minimal interruption.
- Provide updates only at section boundaries and blocker points.
- End the shift with a concise handoff note and exact next file.
