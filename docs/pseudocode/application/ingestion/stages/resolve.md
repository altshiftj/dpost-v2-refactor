---
id: application/ingestion/stages/resolve.py
origin_v1_files:
  - src/dpost/application/processing/device_resolver.py
lane: Processing-Kernel
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Resolve device/plugin and create candidate metadata.

## Origin Gist
- Source mapping: `src/dpost/application/processing/device_resolver.py`.
- Legacy gist: Owns resolve stage for device and plugin matching.

## V2 Improvement Intent
- Transform posture: Move.
- Target responsibility: Resolve device/plugin and create candidate metadata.
- Improvement goal: Clarify layer boundaries and naming without changing behavior intent.
## Inputs
- Initial candidate event context.
- Plugin host/catalog and processor factory.
- Runtime/profile settings affecting plugin eligibility.
- Runtime services facade for read-only file metadata lookups.

## Outputs
- `ResolveStageResult` with resolved plugin id and processor descriptor.
- Enriched candidate metadata with resolution fields.
- Terminal reject/failure outcome when no valid processor can be resolved.
- Stage diagnostics for selection reasoning.

## Invariants
- Resolve stage does not mutate files or records.
- At most one plugin/processor pair is chosen per candidate.
- Resolution logic is deterministic for same candidate + catalog state.
- Stage returns one explicit terminal type on failure (`rejected` or `failed`).

## Failure Modes
- No compatible processor yields reject outcome with reason code.
- Ambiguous processor match yields failure outcome requiring operator/config fix.
- File metadata read failure yields retryable or terminal failure via policy mapping.
- Processor contract violation yields terminal failure outcome.

## Pseudocode
1. Build initial candidate metadata from observer event and file facts.
2. Query processor factory with candidate + profile context.
3. If no processor is found, return terminal reject result with normalized reason code.
4. If processor selection succeeds, enrich candidate with plugin/processor descriptor.
5. Validate resolved candidate completeness and return continue result for stabilize stage.
6. Attach deterministic diagnostics fields (selected plugin id, match reason, cache hit flag).

## Tests To Implement
- unit: deterministic processor selection, no-match/ambiguous-match handling, and non-mutating behavior.
- integration: engine resolve stage maps plugin discovery/factory errors into expected reject/failure outcomes and forwards enriched candidate on success.



