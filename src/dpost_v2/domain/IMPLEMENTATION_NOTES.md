# V2 Domain Core Models: Implementation Notes

Date: 2026-03-04
Lane: `domain-core-models`
Scope: `src/dpost_v2/domain/**` and `tests/dpost_v2/domain/**`

## Goal
Implement V2 domain models and pure rules from pseudocode using strict TDD order:
1. Write failing deterministic tests.
2. Implement minimal logic to pass.
3. Refactor while keeping tests green.

## Canonical Inputs Used
- `docs/pseudocode/domain/naming/identifiers.md`
- `docs/pseudocode/domain/naming/prefix_policy.md`
- `docs/pseudocode/domain/naming/policy.md`
- `docs/pseudocode/domain/routing/rules.md`
- `docs/pseudocode/domain/processing/models.md`
- `docs/pseudocode/domain/processing/batch_models.md`
- `docs/pseudocode/domain/processing/text.md`
- `docs/pseudocode/domain/processing/staging.md`
- `docs/pseudocode/domain/records/local_record.md`
- `docs/planning/20260303-v2-cleanroom-rewrite-blueprint-rpc.md`
- `docs/planning/20260303-v1-to-v2-exhaustive-file-mapping-rpc.md`

## Delivered Domain Modules
- `domain/naming/identifiers.py`
  - typed parse/compose/validate workflow with separator rules, token constraints, canonicalization, and typed errors
- `domain/naming/prefix_policy.py`
  - deterministic precedence-based derivation, ambiguity detection, fallback handling, typed configuration and token-format errors
- `domain/naming/policy.py`
  - template-driven canonical name composition, required-segment checks, segment validation, max-length enforcement, stable identity hash
- `domain/routing/rules.py`
  - deterministic route rule ordering, ambiguity checks, default route behavior, destination validation, typed errors
- `domain/processing/models.py`
  - immutable status/reason/outcome models, retry metadata invariants, serialization and classification conversion helpers
- `domain/processing/batch_models.py`
  - immutable batch outcome model, duplicate member rejection, aggregate and grouped counts, derived batch status
- `domain/processing/text.py`
  - deterministic parse/normalize helpers, encoding-hint handling, malformed-structure errors, header and row-shape validation
- `domain/processing/staging.py`
  - finite state transition engine with terminal-state lock, illegal transition rejection, reason requirements, attempt-index ordering checks
- `domain/records/local_record.py`
  - immutable local record entity with identity invariants, monotonic revision, sync transition validation, timestamp ordering checks

## Test Coverage Added
- `tests/dpost_v2/domain/naming/test_identifiers.py`
- `tests/dpost_v2/domain/naming/test_prefix_policy.py`
- `tests/dpost_v2/domain/naming/test_policy.py`
- `tests/dpost_v2/domain/routing/test_rules.py`
- `tests/dpost_v2/domain/processing/test_models.py`
- `tests/dpost_v2/domain/processing/test_batch_models.py`
- `tests/dpost_v2/domain/processing/test_text.py`
- `tests/dpost_v2/domain/processing/test_staging.py`
- `tests/dpost_v2/domain/records/test_local_record.py`

Coverage intent:
- happy paths and deterministic ordering
- invalid configuration paths
- typed error conditions
- invariant enforcement from pseudocode contracts
- integration-style checks across naming submodules

## TDD Execution Summary
1. Added V2 domain tests first; initial run failed at import (`ModuleNotFoundError: dpost_v2`) as expected.
2. Implemented minimal module surface and domain logic to satisfy contracts.
3. Ran tests, fixed one contract mismatch in naming segment constraints.
4. Ran lint, fixed one unused import.
5. Re-ran lint/tests until clean.

## Validation Commands and Final Results
- `python -m pytest -q tests/dpost_v2/domain`
  - final: `63 passed`
- `python -m ruff check src/dpost_v2 tests/dpost_v2`
  - final: `All checks passed`

## Design and Boundary Notes
- Domain layer remains pure and side-effect free.
- No filesystem/network/UI/runtime adapter behavior was introduced.
- Typed errors are explicit to keep application-layer orchestration deterministic.

## Assumptions and Risks
- Current implementation matches the pseudocode set available on 2026-03-04; future pseudocode revisions may require updates.
- Default token-format patterns were chosen to satisfy current contract tests and may need tuning for strict parity scenarios.
- Cross-lane integration may drive minor API shape changes once application contract owners finalize shared boundaries.
