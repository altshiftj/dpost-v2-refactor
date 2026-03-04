Next-4 Launch Pack (Implementation + TDD)

Use `codex:lanes:prep-next-4` to open terminals and copy this pack.
Then copy the lane-specific prompt for each terminal:
- `lane:prompt:docs-pseudocode-traceability:copy`
- `lane:prompt:ci-v2-gates:copy`
- `lane:prompt:infrastructure-adapters:copy`
- `lane:prompt:plugins-device-system:copy`

Prompt file paths:
- docs/ops/lane-prompts/docs-pseudocode-traceability.md
- docs/ops/lane-prompts/ci-v2-gates.md
- docs/ops/lane-prompts/infrastructure-adapters.md
- docs/ops/lane-prompts/plugins-device-system.md

- Agents are expected to run fully autonomous to completion (no human in the loop).
- Only intervene on hard blockers (credentials, unavailable required systems, contradictory instructions).
- This wave targets implementation in `src/dpost_v2` and `tests/dpost_v2`.
- `docs-pseudocode-traceability` and `ci-v2-gates` are first-pass execution lanes.
- `infrastructure-adapters` and `plugins-device-system` are Phase 2 hardening + gap-closure passes.
- TDD order is mandatory (failing tests -> code -> refactor).
- Run each lane from its dedicated `.worktrees/<lane>` checkout, never from the `D:\Repos\d-post` root checkout.
- Keep one lane per branch and avoid cross-lane edits.
