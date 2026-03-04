Gap-Closure-4 Launch Pack (Implementation + TDD)

Use `codex:lanes:prep-gap-closure-4` to open terminals and copy this pack.
Then copy the lane-specific prompt for each terminal:
- `lane:prompt:startup-bootstrap:copy`
- `lane:prompt:records-core:copy`
- `lane:prompt:plugins-device-system:copy`
- `lane:prompt:docs-pseudocode-traceability:copy`

Prompt file paths:
- docs/ops/lane-prompts/startup-bootstrap.md
- docs/ops/lane-prompts/records-core.md
- docs/ops/lane-prompts/plugins-device-system.md
- docs/ops/lane-prompts/docs-pseudocode-traceability.md

- Agents are expected to run fully autonomous to completion (no human in the loop).
- Only intervene on hard blockers (credentials, unavailable required systems, contradictory instructions).
- This wave targets traceability gap closure in `src/dpost_v2` and `tests/dpost_v2`.
- TDD order is mandatory (failing tests -> code -> refactor).
- Run each lane from its dedicated `.worktrees/<lane>` checkout, never from the `D:\Repos\d-post` root checkout.
- Keep one lane per branch and avoid cross-lane edits.
