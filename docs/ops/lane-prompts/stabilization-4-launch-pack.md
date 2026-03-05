Stabilization-4 Launch Pack (V2 Runtime Hardening)

Use `codex:lanes:setup-stabilization-worktrees` first (idempotent).
Use `codex:lanes:prep-stabilization-4` to open terminals and copy this pack.
Then copy the lane-specific prompt for each terminal:
- `lane:prompt:stabilization-runtime-resilience:copy`
- `lane:prompt:stabilization-ingestion-robustness:copy`
- `lane:prompt:stabilization-observability-quality:copy`
- `lane:prompt:stabilization-ci-reliability:copy`

Prompt file paths:
- docs/ops/lane-prompts/stabilization-runtime-resilience.md
- docs/ops/lane-prompts/stabilization-ingestion-robustness.md
- docs/ops/lane-prompts/stabilization-observability-quality.md
- docs/ops/lane-prompts/stabilization-ci-reliability.md

- Agents are expected to run fully autonomous to completion (no human in the loop).
- Only intervene on hard blockers (credentials, unavailable required systems, contradictory instructions).
- This wave targets resilience and observability quality, not architecture reshaping.
- Run each lane from its dedicated `.worktrees/<lane>` checkout, never from the `D:\Repos\d-post` root checkout.
- Keep one lane per branch and avoid cross-lane edits.
