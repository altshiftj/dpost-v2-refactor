---
id: application/ingestion/models/candidate.py
origin_v1_files:
  - src/dpost/application/processing/candidate_metadata.py
lane: Processing-Kernel
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Candidate artifact metadata model and helper constructors.

## Origin Gist
- Source mapping: `src/dpost/application/processing/candidate_metadata.py`.
- Legacy gist: Defines candidate metadata model for resolve/route.

## V2 Improvement Intent
- Transform posture: Move.
- Target responsibility: Candidate artifact metadata model and helper constructors.
- Improvement goal: Clarify layer boundaries and naming without changing behavior intent.
## Inputs
- Source event metadata (path, observed event type, observed timestamp).
- Filesystem facts (size, modified time, hash/fingerprint where available).
- Resolve-stage hints (detected device id, profile hint, plugin hint).
- Optional route/persist enrichment data added by later stages.

## Outputs
- Immutable candidate metadata model consumed by all ingestion stages.
- Constructor helpers (`from_event`, `with_resolution`, `with_route`, `with_persist_result`).
- Deterministic candidate identity token used by dedupe and tracing.
- Validation errors for malformed paths or unsupported candidate shapes.

## Invariants
- Candidate identity token is deterministic for identical normalized source facts.
- Source path is normalized and non-empty.
- Stage enrichment creates new candidate instances; prior state is unchanged.
- Candidate metadata remains serializable for event/log payloads.

## Failure Modes
- Invalid/missing source path raises `CandidatePathError`.
- Unsupported event type for ingestion raises `CandidateEventTypeError`.
- Invalid enrichment state transition raises `CandidateTransitionError`.
- Non-serializable metadata values raise `CandidateSerializationError`.

## Pseudocode
1. Define frozen candidate model fields for source event facts, detection hints, and stage enrichment slots.
2. Implement `from_event(event, fs_facts)` to normalize path/timestamps and build initial candidate identity token.
3. Implement enrichment helpers returning new candidate instances for resolve, route, and persist phases.
4. Validate required fields and transition legality in each helper.
5. Implement `to_payload()` serializer for events and diagnostics.
6. Expose deterministic hash/key helper used by modified-event gate and retry planner.

## Tests To Implement
- unit: identity determinism, path normalization, immutable enrichment helpers, and invalid transition rejection.
- integration: resolve -> route -> persist stage chain enriches one candidate instance lineage without mutating prior snapshots.



