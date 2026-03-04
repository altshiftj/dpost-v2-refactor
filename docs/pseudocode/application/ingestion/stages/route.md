---
id: application/ingestion/stages/route.py
origin_v1_files:
  - src/dpost/application/processing/route_context_policy.py
  - src/dpost/application/processing/routing.py
lane: Processing-Kernel
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Route decision orchestration using domain routing + naming policy.

## Origin Gist
- Source mapping: `src/dpost/application/processing/route_context_policy.py`, `src/dpost/application/processing/routing.py`.
- Legacy gist: Merges route context assembly into route stage. Owns application route stage orchestration.

## V2 Improvement Intent
- Transform posture: Merge, Move.
- Target responsibility: Route decision orchestration using domain routing + naming policy.
- Improvement goal: Consolidate duplicated logic into a single canonical owner. Clarify layer boundaries and naming without changing behavior intent.
## Inputs
- Stabilized candidate metadata and runtime naming settings.
- Domain routing rules and naming policy functions.
- Force-path override policy and optional operator override input.
- Target root directories and existing-path probe helpers from runtime services.

## Outputs
- `RouteStageResult` with target route decision and terminal type `routed` or `rejected`.
- Enriched candidate with canonical target filename/path tokens.
- Rejection outcome when routing constraints cannot be satisfied.
- Route diagnostics (rule matched, prefix used, override applied/ignored).

## Invariants
- Routing decision is deterministic for identical candidate + settings inputs.
- Domain naming/routing functions are used as pure functions with no adapter side effects.
- Force-path overrides cannot bypass safety guard checks.
- Route stage returns exactly one explicit terminal type on failure (`rejected`).

## Failure Modes
- No matching routing rule yields reject outcome with reason code.
- Naming policy generation failure yields failure outcome with mapped severity.
- Force-path guard violation yields reject outcome.
- Target path validation/probe failure yields retryable or terminal failure per policy.

## Pseudocode
1. Build route context from candidate metadata and naming/routing settings.
2. If force-path input exists, evaluate it through force-path policy and branch on apply/ignore/reject.
3. Run domain routing rules to select destination bucket/root and naming policy to compose final filename.
4. Validate resulting target path against allowed roots and collision precheck strategy.
5. Return routed result with enriched candidate when valid, otherwise return reject/failure outcome.
6. Attach deterministic diagnostics fields used by persist stage and observability.

## Tests To Implement
- unit: deterministic rule precedence, naming composition behavior, force-path policy integration, and reject path handling.
- integration: route stage cooperates with domain naming/routing and persist stage receives stable target paths across retries.



