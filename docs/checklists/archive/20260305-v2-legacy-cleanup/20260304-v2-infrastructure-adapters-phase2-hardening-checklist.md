# Checklist: V2 Infrastructure-Adapters Phase 2 Hardening

## Objective
- Capture reliability and failure-path gap closure completed in lane `infrastructure-adapters` for storage, sync, runtime UI, and observability adapters.

## Reference Set
- `docs/pseudocode/infrastructure/storage/file_ops.md`
- `docs/pseudocode/infrastructure/storage/staging_dirs.md`
- `docs/pseudocode/infrastructure/sync/noop.md`
- `docs/pseudocode/infrastructure/sync/kadi.md`
- `docs/pseudocode/infrastructure/runtime/ui/desktop.md`
- `docs/pseudocode/infrastructure/runtime/ui/dialogs.md`
- `docs/pseudocode/infrastructure/runtime/ui/tkinter.md`
- `docs/pseudocode/infrastructure/observability/metrics.md`
- `docs/planning/20260303-v2-cleanroom-rewrite-blueprint-rpc.md`
- `docs/planning/20260303-v1-to-v2-exhaustive-file-mapping-rpc.md`

## Section: TDD Execution Order
- Why this matters: hardening slices are only trustworthy when failure behavior is test-driven and then minimally implemented.

### Checklist
- [x] Added failing tests first for UI adapter contract boundary, sync malformed input, storage cleanup safety, and metrics non-finite value handling.
- [x] Implemented minimal adapter code updates under `src/dpost_v2/infrastructure/**` to satisfy those failures.
- [x] Re-ran targeted tests to confirm each red-path slice turned green before full suite validation.

### Manual Check
- [x] `python -m pytest -q tests/dpost_v2/infrastructure/runtime/ui/test_desktop.py tests/dpost_v2/infrastructure/sync tests/dpost_v2/infrastructure/storage/test_staging_dirs.py tests/dpost_v2/infrastructure/storage/test_adapter_integration.py tests/dpost_v2/infrastructure/observability/test_metrics.py tests/dpost_v2/infrastructure/observability/test_adapter_integration.py`

### Completion Notes
- How it was done: red-state was recorded first (`7 failed`), then minimal fixes were applied and targeted tests passed (`35 passed`).

---

## Section: Runtime UI Adapter Boundary Hardening
- Why this matters: desktop orchestration must correctly bridge dialog helper and tkinter adapter contracts to avoid runtime prompt failures.

### Checklist
- [x] Added integration-style test for `DesktopUiAdapter + dispatch_dialog + TkinterUiAdapter`.
- [x] Updated `DesktopUiAdapter.prompt` to use a bridge callable that translates dialog request shape into backend prompt kwargs.
- [x] Added request-shape validation in bridge path to keep failures typed and explicit.

### Manual Check
- [x] `python -m pytest -q tests/dpost_v2/infrastructure/runtime/ui/test_desktop.py`

### Completion Notes
- How it was done: replaced direct method handoff (`backend_prompt=self._backend.prompt`) with `_dispatch_backend_prompt(...)` to align signature and preserve dialog normalization.

---

## Section: Sync Adapter Failure-Path Hardening
- Why this matters: sync adapters should fail fast on malformed contract input and avoid transport side effects for invalid requests.

### Checklist
- [x] Added test for `NoopSyncAdapter` rejecting requests without `record_id`.
- [x] Added test for `KadiSyncAdapter` rejecting requests without `record_id` before client transport invocation.
- [x] Enforced explicit `request.record_id` validation in both adapters.

### Manual Check
- [x] `python -m pytest -q tests/dpost_v2/infrastructure/sync`

### Completion Notes
- How it was done: `NoopSyncAdapter.sync_record` now raises `NoopSyncInputError` for missing `record_id`, and `KadiSyncAdapter.sync_record` now raises `KadiSyncResponseError` before any remote call.

---

## Section: Storage Safety Hardening
- Why this matters: cleanup candidate derivation must remain root-scoped to prevent accidental retention/deletion behavior outside configured storage boundaries.

### Checklist
- [x] Added test ensuring `cleanup_candidates(...)` excludes paths outside `layout.root`.
- [x] Added integration-style test proving `derive_staging_layout(...)` and `LocalFileOpsAdapter.move(...)` interoperate at bucket boundaries.
- [x] Updated cleanup filter logic to drop out-of-root candidates deterministically.

### Manual Check
- [x] `python -m pytest -q tests/dpost_v2/infrastructure/storage/test_staging_dirs.py tests/dpost_v2/infrastructure/storage/test_adapter_integration.py`

### Completion Notes
- How it was done: `cleanup_candidates(...)` now applies root-scope filtering before intake/staging exclusions.

---

## Section: Observability Hardening
- Why this matters: metrics adapters must reject invalid values to keep downstream backends and alerting pipelines stable.

### Checklist
- [x] Added failure-path test for non-finite metric values (`nan`, `inf`, `-inf`).
- [x] Added integration-style observability test across tracing, logging, and metrics adapter boundaries.
- [x] Enforced finite-value validation in metrics normalization.

### Manual Check
- [x] `python -m pytest -q tests/dpost_v2/infrastructure/observability/test_metrics.py tests/dpost_v2/infrastructure/observability/test_adapter_integration.py`

### Completion Notes
- How it was done: `MetricsAdapter._normalize_value(...)` now checks `math.isfinite(...)` and raises `MetricsValueError` for non-finite numbers.

---

## Section: Final Validation and Checkpoint
- Why this matters: lane completion requires reproducible quality gates and an auditable checkpoint commit.

### Checklist
- [x] Ran lint gate on V2 source/tests.
- [x] Ran full lane test suite (`tests/dpost_v2/infrastructure`).
- [x] Ran full V2 test suite (`tests/dpost_v2`) for regression confidence.
- [x] Committed lane slice checkpoint.

### Manual Check
- [x] `python -m ruff check src/dpost_v2 tests/dpost_v2`
- [x] `python -m pytest -q tests/dpost_v2/infrastructure`
- [x] `python -m pytest -q tests/dpost_v2`
- [x] `git show --stat --oneline dca01d4`

### Completion Notes
- How it was done: all validation gates passed (`78` infrastructure tests and `324` total V2 tests), then committed as `dca01d4` with message `v2: infrastructure adapters harden failure paths`.

---

## Section: Risks and Assumptions
- Why this matters: documents current behavior boundaries for downstream integration lanes.

### Checklist
- [x] Recorded assumption that sync requests missing `record_id` are invalid at infrastructure boundary.
- [x] Recorded behavior that out-of-root storage cleanup candidates are ignored, not raised.
- [x] Recorded behavior that non-finite metrics are rejected with typed adapter error.

### Manual Check
- [x] Review implementation and tests in:
- [x] `src/dpost_v2/infrastructure/sync/{noop.py,kadi.py}`
- [x] `src/dpost_v2/infrastructure/storage/staging_dirs.py`
- [x] `src/dpost_v2/infrastructure/observability/metrics.py`

### Completion Notes
- How it was done: assumptions were constrained to infrastructure adapter contracts and codified with deterministic tests.
