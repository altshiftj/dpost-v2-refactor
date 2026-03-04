---
id: application/ingestion/processor_factory.py
origin_v1_files:
  - src/dpost/application/processing/processor_factory.py
lane: Processing-Kernel
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Select and instantiate processor from plugin registry + context.

## Origin Gist
- Source mapping: `src/dpost/application/processing/processor_factory.py`.
- Legacy gist: Selects processor implementation from plugin contracts.

## V2 Improvement Intent
- Transform posture: Move.
- Target responsibility: Select and instantiate processor from plugin registry + context.
- Improvement goal: Clarify layer boundaries and naming without changing behavior intent.
## Inputs
- Candidate metadata from resolve stage (device hints, file signature, profile).
- Plugin host/catalog lookup interfaces.
- Runtime/profile settings affecting processor selection.
- Optional processor instance cache keyed by plugin id + profile + processor type.

## Outputs
- Concrete processor instance implementing plugin processor contract.
- Processor selection descriptor (selected plugin, capability reason, cache hit/miss).
- Typed selection errors for no-match, ambiguous-match, and initialization failures.
- Optional fallback decision (`reject`, `retry`, or `default_processor`) based on policy.

## Invariants
- Selection is deterministic for identical candidate + profile + catalog state.
- At most one processor is selected for a candidate event.
- Cache entries are reused only when plugin version/capability fingerprint matches.
- Factory never reaches into plugin internals outside declared contracts.

## Failure Modes
- No compatible plugin yields `ProcessorNotFoundError`.
- Multiple equally ranked matches yield `ProcessorAmbiguousMatchError`.
- Plugin factory raising exception yields `ProcessorInitializationError`.
- Contract non-conformance of returned processor yields `InvalidProcessorError`.

## Pseudocode
1. Query plugin catalog for processors compatible with candidate type/profile/device hints.
2. Rank candidates by explicit capability match rules and deterministic tie-breaker.
3. If cache is enabled, reuse existing processor instance when cache key matches current plugin fingerprint.
4. Instantiate processor via plugin contract factory when cache miss occurs.
5. Validate returned processor against contract surface and return selection descriptor.
6. On selection failures, return typed error used by resolve/engine failure policies.

## Tests To Implement
- unit: deterministic ranking, ambiguity detection, cache reuse/invalidation, and contract validation of processor instances.
- integration: resolve stage + processor factory chooses the expected plugin for multiple profiles and maps plugin init errors to normalized ingestion outcomes.



