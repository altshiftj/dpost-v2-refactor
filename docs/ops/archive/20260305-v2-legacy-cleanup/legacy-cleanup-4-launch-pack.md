ARCHIVE STATUS:
- Historical lane-pack prompt from V2 cutover.
- Retained for audit traceability; not an active runtime/runbook target.

Legacy-Cleanup-4 Launch Pack (Retirement + Alignment)

Use `codex:lanes:prep-cleanup-4` to open terminals and copy this pack.
Then copy the lane-specific prompt for each terminal:
- `lane:prompt:legacy-runtime-cutover:copy`
- `lane:prompt:legacy-code-retirement:copy`
- `lane:prompt:legacy-tests-retirement:copy`
- `lane:prompt:legacy-docs-tooling:copy`

Prompt file paths:
- docs/ops/lane-prompts/legacy-runtime-cutover.md
- docs/ops/lane-prompts/legacy-code-retirement.md
- docs/ops/lane-prompts/legacy-tests-retirement.md
- docs/ops/lane-prompts/legacy-docs-tooling.md

- Agents are expected to run fully autonomous to completion (no human in the loop).
- Only intervene on hard blockers (credentials, unavailable required systems, contradictory instructions).
- This wave retires legacy `src/dpost` + legacy test surfaces while preserving the `dpost` command name on V2.
- Run each lane from its dedicated `.worktrees/<lane>` checkout, never from the `D:\Repos\d-post` root checkout.
- Keep one lane per branch and avoid cross-lane edits.
