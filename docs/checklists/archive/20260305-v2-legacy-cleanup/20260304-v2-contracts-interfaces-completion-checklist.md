# Checklist: V2 Contracts-Interfaces Lane Completion

## Objective
- Verify that the V2 `contracts-interfaces` lane implementation matches pseudocode intent and is fully validated.

## Reference Set
- `docs/pseudocode/application/contracts/context.md`
- `docs/pseudocode/application/contracts/events.md`
- `docs/pseudocode/application/contracts/ports.md`
- `docs/pseudocode/application/contracts/plugin_contracts.md`
- `docs/planning/20260303-v2-cleanroom-rewrite-blueprint-rpc.md`
- `docs/planning/20260303-v1-to-v2-exhaustive-file-mapping-rpc.md`

## Section: Context Contracts
- Why this matters: `RuntimeContext` and `ProcessingContext` are shared dependencies for startup/runtime/ingestion lanes; any drift here causes cross-lane breakage.

### Checklist
- [x] Implement immutable `RuntimeContext` and `ProcessingContext`.
- [x] Implement constructor helpers and validators (`from_settings`, `for_candidate`, `validate_*`).
- [x] Implement clone helpers (`with_retry`, `with_failure`, `with_route`) with retry monotonicity checks.
- [x] Implement typed validation errors for missing/invalid context state.

### Manual Check
- [x] `python -m pytest -q tests/dpost_v2/application/contracts/test_context.py`

### Completion Notes
- How it was done: test-first slices added for normalization, invariants, clone behavior, and failure modes; implementation completed to satisfy all tests.

---

## Section: Event Contracts
- Why this matters: event contracts are consumed across UI/runtime/observability and must keep stable wire values and payload shape.

### Checklist
- [x] Implement `EventKind`, `EventSeverity`, and `EventStage` enums with explicit wire values.
- [x] Implement base and specialized event dataclasses with typed validation.
- [x] Implement deterministic `event_from_outcome`.
- [x] Implement `to_payload` serializer with payload serializability checks.

### Manual Check
- [x] `python -m pytest -q tests/dpost_v2/application/contracts/test_events.py`

### Completion Notes
- How it was done: tests were added for enum stability, correlation/timestamp validation, deferred/failure mappings, and serialization; event contract implementation now passes all.

---

## Section: Port Contracts
- Why this matters: ports are the application-to-infrastructure seam; deterministic binding validation prevents composition-time ambiguity.

### Checklist
- [x] Implement runtime-checkable protocols for all required ports.
- [x] Implement `validate_port_bindings` with missing/unknown/non-conformant detection.
- [x] Implement typed port error taxonomy.
- [x] Implement normalized sync request/response envelopes and result envelope invariants.

### Manual Check
- [x] `python -m pytest -q tests/dpost_v2/application/contracts/test_ports.py`

### Completion Notes
- How it was done: tests first for binding matrix behavior and envelope validation; implementations hardened until all protocol/binding and error-path tests passed.

---

## Section: Plugin Contracts
- Why this matters: plugin discovery/host/factory lanes depend on stable plugin metadata/capability and processor contract semantics.

### Checklist
- [x] Implement plugin metadata/capabilities/descriptor/result dataclasses.
- [x] Implement device/pc/processor protocols.
- [x] Implement `validate_plugin_contract` (missing exports, duplicates, capability combinations, processor factory conformance, version compatibility).
- [x] Implement `validate_processor_result` normalization and validation.

### Manual Check
- [x] `python -m pytest -q tests/dpost_v2/application/contracts/test_plugin_contracts.py`

### Completion Notes
- How it was done: test-first slices expanded to include duplicate-id rejection, incompatible capability combinations, and invalid processor factory returns; implementation updated accordingly.

---

## Section: Package Contract Surface
- Why this matters: downstream lanes import from `dpost_v2.application.contracts`; export drift here breaks integration unexpectedly.

### Checklist
- [x] Implement stable re-export surface in `src/dpost_v2/application/contracts/__init__.py`.
- [x] Lock expected symbols with contract export tests.

### Manual Check
- [x] `python -m pytest -q tests/dpost_v2/contracts/test_contract_exports.py`

### Completion Notes
- How it was done: cross-module symbol tests were added first; missing exports were then added to `__all__` and module re-exports.

---

## Section: Lane Validation Gate
- Why this matters: final lane handoff requires reproducible green checks across the entire lane test tree.

### Checklist
- [x] Run lint for lane-scoped code/tests.
- [x] Run full `tests/dpost_v2` suite.
- [x] Record checkpoint commit.

### Manual Check
- [x] `python -m ruff check src/dpost_v2/application/contracts tests/dpost_v2/application/contracts tests/dpost_v2/contracts`
- [x] `python -m pytest -q tests/dpost_v2`
- [x] `git show --stat --oneline -1`

### Completion Notes
- How it was done: final gate passed with `46` tests green; implementation checkpoint committed as `cfc6d17`.
