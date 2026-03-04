---
id: application/ingestion/stages/persist.py
origin_v1_files:
  - src/dpost/application/processing/record_flow.py
  - src/dpost/application/processing/record_persistence_context.py
  - src/dpost/application/processing/record_utils.py
  - src/dpost/application/processing/rename_flow.py
lane: Processing-Kernel
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Persist/rename/reject flows and record update integration.

## Origin Gist
- Source mapping: 4 origin files (see front matter origin_v1_files).
- Legacy gist: Owns record persistence stage execution path. Co-locates persistence context model with persist stage, and consolidates the remaining mapped persistence helpers under the same stage boundary.

## V2 Improvement Intent
- Transform posture: Merge, Move.
- Target responsibility: Persist/rename/reject flows and record update integration.
- Improvement goal: Consolidate duplicated logic into a single canonical owner. Clarify layer boundaries and naming without changing behavior intent.
## Inputs
- Routed candidate with final target path and naming metadata.
- Runtime services for file operations and record persistence.
- Records service and retry planner policies.
- Persist settings (collision behavior, overwrite rules, temp-to-final move strategy).

## Outputs
- `PersistStageResult` with terminal type `persisted`, `retry`, `rejected`, or `failed`.
- Persisted/updated record snapshot when persistence succeeds.
- File operation trace describing rename/move/copy actions.
- Normalized failure outcome and retry plan for recoverable persistence failures.

## Invariants
- Persist stage is the only ingestion stage that mutates file location and record store state.
- A successful persist creates exactly one durable record mutation for the candidate.
- Retrying persist with same event id is idempotent with respect to final file path and record identity.
- Stage returns one explicit terminal result type on every execution path.

## Failure Modes
- Target path collision under reject policy yields `rejected` terminal outcome.
- File move/rename permission or lock failures yield retryable or terminal failure via policy.
- Record store conflict/version mismatch yields retry/failure based on configured conflict policy.
- Partial side-effect detection (file moved but record save failed) yields compensating action outcome.

## Pseudocode
1. Validate routed target path and persist policy preconditions.
2. Execute file operation strategy (atomic move/rename when possible) through runtime services.
3. Build or update domain record via records service and persist mutation.
4. If file operation or record save fails, classify failure and compute retry plan.
5. If partial success occurred, run compensating action policy and return typed outcome.
6. Return `persisted` result with record snapshot and operation trace on success.

## Tests To Implement
- unit: collision policy handling, idempotent retry behavior, partial-failure compensation, and retry-plan generation.
- integration: route->persist->records service flow creates/updates records and handles file or store failures with deterministic terminal outcomes.



