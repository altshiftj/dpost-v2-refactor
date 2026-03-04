---
id: application/ingestion/policies/error_handling.py
origin_v1_files:
  - src/dpost/application/processing/error_handling.py
lane: Processing-Kernel
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Exception-to-outcome mapping and severity classification.

## Origin Gist
- Source mapping: `src/dpost/application/processing/error_handling.py`.
- Legacy gist: Maps exceptions to deterministic pipeline outcomes.

## V2 Improvement Intent
- Transform posture: Move.
- Target responsibility: Exception-to-outcome mapping and severity classification.
- Improvement goal: Clarify layer boundaries and naming without changing behavior intent.
## Inputs
- Raised exception object and originating stage id.
- Processing context (mode, profile, retry attempt, correlation ids).
- Policy configuration table mapping exception classes/codes to severity/retryability.
- Optional fallback mapper for unknown exceptions.

## Outputs
- Normalized error classification (`reason_code`, `severity`, `retryable`, `terminal_type`).
- Structured diagnostics payload suitable for events/logging.
- Mapping decision metadata (rule id matched, fallback used).
- Typed policy errors when configuration is invalid.

## Invariants
- Mapping is deterministic for identical exception + context + policy config.
- Unknown exceptions always map to explicit fallback classification.
- Severity and retryability decisions are decoupled from infrastructure-specific error text.
- Policy module does not emit side effects; it only classifies.

## Failure Modes
- Invalid mapping config (duplicate/ambiguous rules) yields `ErrorHandlingPolicyConfigError`.
- Unsupported exception wrapper shape yields `ErrorHandlingInputError`.
- Fallback mapper failure yields `ErrorHandlingFallbackError`.
- Missing stage id in input yields `ErrorHandlingContextError`.

## Pseudocode
1. Normalize exception into canonical envelope (type, message, optional code, nested cause).
2. Resolve mapping rule by exception type hierarchy, stage id, and optional policy predicates.
3. If no rule matches, apply fallback rule with default severity/retryability.
4. Build normalized classification payload with reason code and terminal type hint.
5. Return classification plus mapping diagnostics for downstream failure outcome policy.
6. Validate mapping table at startup to catch invalid/ambiguous configuration early.

## Tests To Implement
- unit: rule matching precedence, fallback handling, and config validation errors.
- integration: ingestion engine exception paths use error handling policy output to produce consistent failure outcomes/events across multiple stages.



