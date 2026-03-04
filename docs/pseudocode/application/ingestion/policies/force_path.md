---
id: application/ingestion/policies/force_path.py
origin_v1_files:
  - src/dpost/application/processing/force_path_policy.py
lane: Processing-Kernel
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Force-path override policy and guard checks.

## Origin Gist
- Source mapping: `src/dpost/application/processing/force_path_policy.py`.
- Legacy gist: Defines force-path override policy.

## V2 Improvement Intent
- Transform posture: Move.
- Target responsibility: Force-path override policy and guard checks.
- Improvement goal: Clarify layer boundaries and naming without changing behavior intent.
## Inputs
- Candidate metadata and default routed target proposal.
- Optional operator/user force-path override.
- Allowed destination roots and path safety constraints from settings.
- Optional conflict probe helper for existing destination path checks.

## Outputs
- `ForcePathDecision` terminal type (`apply_override`, `ignore_override`, `reject_override`).
- Normalized approved override path when applicable.
- Rejection reason codes for unsafe or invalid overrides.
- Diagnostics showing why override was applied/ignored/rejected.

## Invariants
- Override path normalization happens exactly once before decision.
- Override cannot escape allowed roots (no traversal outside configured scope).
- Decision is deterministic for same inputs and policy configuration.
- Reject decision is explicit terminal type consumed by route stage.

## Failure Modes
- Invalid override path syntax yields `ForcePathFormatError`.
- Override outside allowed roots yields `ForcePathSafetyError`.
- Existing destination conflict under strict policy yields `ForcePathConflictError`.
- Missing candidate/path context yields `ForcePathInputError`.

## Pseudocode
1. If no override is present, return `ignore_override` with passthrough diagnostics.
2. Normalize override path (separator, case, relative segments) against configured root policy.
3. Validate normalized override path against allowed roots and safety constraints.
4. Optionally probe destination conflict policy and reject when strict conflict rules fail.
5. Return `apply_override` with normalized path when all checks pass.
6. Return `reject_override` with reason code for any guard failure.

## Tests To Implement
- unit: override normalization, root-escape rejection, conflict checks, and deterministic decision behavior.
- integration: route stage applies valid force-path overrides and rejects unsafe ones with stable reason codes.



