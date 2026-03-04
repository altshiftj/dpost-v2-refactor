---
id: domain/routing/rules.py
origin_v1_files:
  - src/dpost/domain/processing/routing.py
lane: Domain-Core
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Pure routing rules and deterministic path decision functions.

## Origin Gist
- Source mapping: `src/dpost/domain/processing/routing.py`.
- Legacy gist: Moves routing rules into dedicated domain routing module.

## V2 Improvement Intent
- Transform posture: Move.
- Target responsibility: Pure routing rules and deterministic path decision functions.
- Improvement goal: Clarify layer boundaries and naming without changing behavior intent.
## Inputs
- Route facts derived from candidate/domain metadata (device family, sample category, profile token).
- Ordered routing rule set with predicates and destination tokens.
- Optional default route rule.
- Rule conflict policy settings.

## Outputs
- Route decision model (`matched`, `defaulted`, `rejected`) with destination token set.
- Matched rule metadata (rule id, priority, predicate snapshot).
- Rejection reason codes when no valid rule applies.
- Deterministic comparator helper for rule ordering.

## Invariants
- Rule evaluation order is stable and deterministic.
- Only one highest-priority rule may match for a valid decision.
- Rule evaluation is pure: no external state mutation.
- Example: same route facts always match the same highest-priority rule.
- Counterexample: two equal-priority matching rules is invalid and rejected.

## Failure Modes
- No matching rule and no default route yields `RoutingRuleNotFoundError`.
- Ambiguous equal-priority matches yield `RoutingRuleAmbiguityError`.
- Invalid rule predicate configuration yields `RoutingRuleConfigurationError`.
- Invalid destination token in selected rule yields `RoutingDestinationValidationError`.

## Pseudocode
1. Validate routing rule set for unique ids and deterministic priority ordering.
2. Evaluate each rule predicate against route facts in sorted priority order.
3. Collect matches and enforce single-match-at-highest-priority invariant.
4. If no match, apply default rule when configured; otherwise return rejected decision.
5. Validate destination token set of selected rule.
6. Return route decision model with matched rule diagnostics.

## Tests To Implement
- unit: rule priority ordering, ambiguity rejection, default route behavior, and destination validation.
- integration: application route stage calls routing rules with domain facts and receives deterministic decisions for repeated inputs.



