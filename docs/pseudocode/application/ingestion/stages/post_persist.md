---
id: application/ingestion/stages/post_persist.py
origin_v1_files:
  - src/dpost/application/processing/post_persist_bookkeeping.py
lane: Processing-Kernel
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Post-persist bookkeeping, immediate sync trigger, emission hooks.

## Origin Gist
- Source mapping: `src/dpost/application/processing/post_persist_bookkeeping.py`.
- Legacy gist: Isolates post-persist side effects into dedicated stage.

## V2 Improvement Intent
- Transform posture: Move.
- Target responsibility: Post-persist bookkeeping, immediate sync trigger, emission hooks.
- Improvement goal: Clarify layer boundaries and naming without changing behavior intent.
## Inputs
- Successful or failed `PersistStageResult`.
- Runtime services for event emission, sync trigger, and optional UI notifications.
- Immediate sync policy settings and sync enablement flags.
- Correlation context and persisted record metadata.

## Outputs
- Terminal `PostPersistResult` (`completed`, `completed_with_sync_warning`, `failed`).
- Bookkeeping updates (mark-unsynced flag, sync-attempt metadata, audit stamps).
- Immediate sync trigger outcomes when enabled.
- Failure/event emissions delegated to policy modules.

## Invariants
- Post-persist stage executes only after persist stage terminal result is available.
- Bookkeeping updates are idempotent per event id and record id.
- Immediate sync is attempted at most once per post-persist execution path.
- Post-persist never rewrites routing or naming decisions.

## Failure Modes
- Bookkeeping persistence failure yields terminal failure outcome.
- Immediate sync trigger failure maps to normalized sync warning/failure outcome.
- Event emission failure is captured and returned without corrupting persisted record state.
- Missing persisted record for sync-required flow yields policy violation failure outcome.

## Pseudocode
1. Inspect persist result and short-circuit for non-persisted terminal outcomes when appropriate.
2. Apply bookkeeping mutations (unsynced flag, last-processed metadata, event audit markers).
3. If immediate sync is enabled and persist succeeded, invoke sync trigger via runtime services.
4. Map sync errors through immediate-sync error policy and emit corresponding failure events.
5. Emit post-persist success/failure events with correlation metadata.
6. Return terminal post-persist result containing bookkeeping and sync statuses.

## Tests To Implement
- unit: idempotent bookkeeping updates, immediate-sync branching, and sync-error mapping behavior.
- integration: persist + post-persist + sync adapter flows produce expected unsynced/synced states and failure emissions.



