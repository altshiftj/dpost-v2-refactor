Core-4 Launch Pack (Implementation + TDD)

Use `codex:lanes:prep-core-4` to open terminals and copy this pack.
Then copy the lane-specific prompt for each terminal:
- `lane:prompt:contracts-interfaces:copy`
- `lane:prompt:startup-bootstrap:copy`
- `lane:prompt:domain-core-models:copy`
- `lane:prompt:ingestion-pipeline:copy`

Prompt file paths:
- docs/ops/lane-prompts/contracts-interfaces.md
- docs/ops/lane-prompts/startup-bootstrap.md
- docs/ops/lane-prompts/domain-core-models.md
- docs/ops/lane-prompts/ingestion-pipeline.md

- Agents are expected to run fully autonomous to completion (no human in the loop).
- Only intervene on hard blockers (credentials, unavailable required systems, contradictory instructions).
- This wave targets implementation in `src/dpost_v2` and `tests/dpost_v2`.
- TDD order is mandatory (failing tests -> code -> refactor).
- Keep one lane per branch and avoid cross-lane edits.

