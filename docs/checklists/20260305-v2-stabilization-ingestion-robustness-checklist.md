# Checklist: V2 Stabilization Ingestion Robustness

## Section: Engine Deterministic Failure Normalization
- Why this matters: malformed input payloads or policy exceptions must not crash ingestion orchestration or bypass terminal outcome mapping.

### Checklist
- [x] Added tests for `initial_state_factory` failure fallback to terminal failure.
- [x] Added tests for `error_handling_policy` failure fallback to terminal failure.
- [x] Added tests for `failure_outcome_policy` failure fallback to terminal failure.
- [x] Hardened engine processing to coerce malformed event payloads and safely normalize policy failures.

### Manual Check
- [x] Open `src/dpost_v2/application/ingestion/engine.py` and verify:
- [x] `process()` uses event coercion before state factory + exception normalization.
- [x] `_safe_classification()` and `_safe_failure_outcome()` preserve deterministic terminal mapping.
- [x] Run: `python -m pytest -q tests/dpost_v2/application/ingestion/test_engine.py`

### Completion Notes
- How it was done: tests were added first for state-factory and policy-failure crash paths, then engine normalization was hardened so all such paths return stable `FAILED_TERMINAL` outcomes without violating stage contracts.

---

## Section: Resolve Stage Malformed, Empty, and Partial Inputs
- Why this matters: resolve-stage input quality varies by observer/event source; malformed payloads must terminate deterministically at the resolve boundary.

### Checklist
- [x] Added test to reject empty source path as deterministic resolve rejection.
- [x] Added test to reject unsupported event kind as deterministic resolve rejection.
- [x] Added test to allow partial event input with missing `observed_at` defaulting behavior.
- [x] Hardened resolve stage for fs-facts provider failures and malformed fs-facts payloads.

### Manual Check
- [x] Open `src/dpost_v2/application/ingestion/stages/resolve.py` and verify:
- [x] `CandidateError` maps to `REJECTED` with `reason_code=invalid_candidate`.
- [x] fs-facts provider exceptions map to `FAILED` with `reason_code=fs_facts_unavailable`.
- [x] Non-mapping fs-facts payload maps to `FAILED` with `reason_code=invalid_fs_facts`.
- [x] Run: `python -m pytest -q tests/dpost_v2/application/ingestion/stages/test_resolve_stabilize_route.py`

### Completion Notes
- How it was done: failing tests were introduced for malformed and partial resolve inputs, then resolve-stage guards were added around fs-facts and candidate creation with explicit terminal directives that keep stage semantics intact.

---

## Section: Persist/Post-Persist Retry and Failure Transition Robustness
- Why this matters: malformed retry plans and malformed collaborator diagnostics can cause nondeterministic exceptions unless transitions are explicitly normalized.

### Checklist
- [x] Added test for malformed retry plan (`next_attempt` not numeric) returning terminal failure.
- [x] Added test for malformed sync diagnostics payload using stable fallback reason.
- [x] Hardened persist-stage retry-plan normalization for malformed planner outputs.
- [x] Hardened post-persist diagnostics parsing to tolerate non-mapping payloads.

### Manual Check
- [x] Open `src/dpost_v2/application/ingestion/stages/persist.py` and verify:
- [x] malformed retry planner outputs map to terminal `FAILED` with `reason_code=invalid_retry_plan`.
- [x] valid retry outputs still map to `RETRY` with normalized attempt progression.
- [x] Open `src/dpost_v2/application/ingestion/stages/post_persist.py` and verify malformed diagnostics fallback to `sync_failed`.
- [x] Run: `python -m pytest -q tests/dpost_v2/application/ingestion/stages/test_persist_post_persist.py`

### Completion Notes
- How it was done: tests were added first for malformed collaborator payloads, then minimal parsing/normalization helpers were introduced to preserve deterministic retry and sync-warning transitions.

---

## Section: Validation Gate and Checkpoint
- Why this matters: lane completion requires deterministic test/lint evidence and a traceable checkpoint commit.

### Checklist
- [x] Baseline ingestion suite recorded before changes: `41 passed`.
- [x] Red-phase targeted failures recorded after adding robustness tests.
- [x] Green-phase targeted suite passes after implementation.
- [x] Full ingestion suite passes after hardening changes.
- [x] Ingestion lint gate passes on allowed scope.
- [x] Lane checkpoint commit created.

### Manual Check
- [x] Run: `python -m pytest -q tests/dpost_v2/application/ingestion`
- [x] Run: `python -m ruff check src/dpost_v2/application/ingestion tests/dpost_v2/application/ingestion`
- [x] Run: `git log -1 --oneline`
- [x] Verify commit: `c033389 v2: stabilization-ingestion-robustness harden malformed failures`

### Completion Notes
- How it was done: robustness work followed TDD order (red -> green -> refactor), passed lane-targeted validation, and was checkpointed in one commit for reviewable traceability.
