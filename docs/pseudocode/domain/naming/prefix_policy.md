---
id: domain/naming/prefix_policy.py
origin_v1_files:
  - src/dpost/domain/naming/prefix_policy.py
lane: Domain-Core
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Prefix derivation rules independent of infrastructure concerns.

## Origin Gist
- Source mapping: `src/dpost/domain/naming/prefix_policy.py`.
- Legacy gist: Retains pure naming rule module prefix_policy.py.

## V2 Improvement Intent
- Transform posture: Migrate.
- Target responsibility: Prefix derivation rules independent of infrastructure concerns.
- Improvement goal: Carry forward stable behavior while enforcing V2 contracts and explicit context.
## Inputs
- Normalized domain attributes used for prefix derivation (device family, process type, profile token).
- Prefix rule set with precedence ordering.
- Optional fallback prefix token for unmatched attribute combinations.
- Validation rules for prefix token format.

## Outputs
- Derived prefix token and derivation reason metadata.
- Prefix decision model (`derived`, `fallback`, `rejected`).
- Rule-match diagnostics for explainability.
- Validation errors for malformed prefix outputs.

## Invariants
- Prefix derivation is deterministic for identical attributes and rule set.
- Derived prefix tokens always satisfy token-format rules.
- Rule precedence is explicit and stable.
- Example: attributes `{device_family: "rheometer", profile: "prod"}` map to a fixed prefix token.
- Counterexample: conflicting rules with same priority for one attribute set are invalid.

## Failure Modes
- No rule and no fallback token yields `PrefixDerivationNotFoundError`.
- Malformed derived token yields `PrefixTokenFormatError`.
- Ambiguous top-priority rule match yields `PrefixRuleAmbiguityError`.
- Invalid rule configuration yields `PrefixRuleConfigurationError`.

## Pseudocode
1. Validate prefix rule set structure and precedence ordering.
2. Evaluate rules against normalized attribute set in deterministic priority order.
3. Select first matching rule and extract candidate prefix token.
4. If no rule matches, apply fallback token when configured; otherwise return not-found error.
5. Validate final prefix token against format constraints and build decision model.
6. Return token plus derivation diagnostics for downstream naming policy use.

## Tests To Implement
- unit: precedence behavior, ambiguity detection, fallback handling, and token format validation.
- integration: naming policy uses prefix policy outputs consistently across profiles and rejects ambiguous prefix configurations.



