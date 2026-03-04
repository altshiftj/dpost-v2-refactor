# AI Agent Instructions (dpost)

## Purpose
- Task focus (current run): populate V2 pseudocode documents in `docs/pseudocode/` with concrete implementation intent.
- Preserve traceability to migration mapping so models can execute V2 implementation in parallel without interpretation drift.
- Keep work reviewable, deterministic, and checkpointed.

## Current Phase (Locked)
- Execution target: documentation completion for V2 pseudocode only.
- Canonical artifacts:
  - `docs/planning/20260303-v2-cleanroom-rewrite-blueprint-rpc.md`
  - `docs/planning/20260303-v1-to-v2-exhaustive-file-mapping-rpc.md`
  - `docs/checklists/20260304-v2-pseudocode-population-checklist.md`
  - `docs/pseudocode/`
- Runtime implementation is out of scope until the pseudocode pass is complete.

## Operating Mode
- Autonomous execution is default.
- Work in discrete, high-coherence sections (contracts, startup, domain, ingestion, infrastructure, plugins).
- Continue until the user issues a stop or the checklist is complete.
- Only ask for human input when ambiguity threatens correctness.

## Scope
- Prefer edits under `docs/pseudocode/`, `docs/checklists/`, `docs/planning/`, and `docs/reports/`.
- Do not edit `src/` or `tests/` unless implementation is explicitly resumed.
- Do not touch `.venv/`, lockfiles, build artifacts, or generated files.

## Pseudocode Completion Rules (Mandatory)
Each `.md` under `docs/pseudocode/` must contain:
- `Intent`
- `Inputs`
- `Outputs`
- `Invariants`
- `Failure Modes`
- `Pseudocode`
- `Tests To Implement`
- explicit `origin` or `source` mapping to V1 when applicable.

A file is incomplete if it still contains:
- `TBD`
- placeholder-only language without concrete behavior

## Execution Workflow for This Task
1. Map/align
   - Confirm each target pseudocode file has a mapping path in the file-mapping doc.
2. Populate
   - Replace placeholders with concrete behavior-oriented descriptions.
3. Normalize
   - Normalize terminology and imports/ownership boundaries across sections.
4. Validate
   - Run grep checks and reconcile with checklist completion.
5. Commit
   - Commit section-complete checkpoints with scoped messages.

## Checkpoint and Commit Protocol
- Commit frequently by completed section/lane, not as one giant pass.
- Suggested commit style: `docs: populate v2 pseudocode - <section>`.
- Do not wait for extra approvals for routine documentation edits.

## Planning and Tracking
- Use `docs/checklists/` for execution order and completion state.
- Use `docs/reports/` for summary risk/quality notes.
- Use `docs/planning/` for any architecture or scope changes.
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
- Document ownership per layer; do not mix concrete adapter behavior into domain/application files.

## Commands
- Documentation validation:
  - `rg "TBD" docs/pseudocode`
  - `rg "origin|source|v1" docs/pseudocode -n`
  - `git status`
  - `git diff`
- Optional quality gate: `python -m pre_commit run --all-files`

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
- If new internal terms are introduced in pseudocode or planning docs, add/update entries in `GLOSSARY.csv` at repo root.
- Required columns: `term,type,purpose,usage`.

## Output Expectations
- At section completion, report:
  - files modified,
  - checks run,
  - any blocked or deferred items.

## Overnight Autonomous SOP (When Requested)
- Execute all sections continuously in order with minimal interruption.
- Provide updates only at section boundaries and blocker points.
- End the shift with a concise handoff note and exact next file.
