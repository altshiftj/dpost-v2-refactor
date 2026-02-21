# dpost Deep-Core Runtime Retirement Checklist

## Section: Program Guardrails
- Why this matters: Deep-core migration is high risk and needs strict parity
  guardrails to avoid regressions.

### Checklist
- [x] Confirm slice scope and target capability before each implementation.
- [x] Add failing migration boundary tests before code changes.
- [x] Capture red-state evidence for each slice in active reports.
- [x] Require full gate green state before closing each slice.
- [x] Update architecture docs and glossary in the same change set.

### Completion Notes
- How it was done: Processing/storage deep-core increment executed as an
  isolated capability slice with explicit red/green evidence in
  `tests/migration/test_phase10_runtime_app_rehost.py`, followed by required
  migration/lint/format/full-suite gates.

---

## Section: Processing Core Rehost
- Why this matters: Processing orchestration is the largest legacy hotspot and
  controls most runtime behavior.

### Checklist
- [x] Add migration contracts for processing ownership boundaries under
      `dpost/application`.
- [x] Introduce dpost-owned processing models and orchestration services.
- [x] Rehost stage sequencing/retry/reject control flow from legacy
      `FileProcessManager`.
- [x] Preserve route decision and non-ACCEPT handling semantics.
- [x] Remove processing imports from
      `src/dpost/application/runtime/runtime_dependencies.py`.
- [x] Verify migration and full gates are green.

### Completion Notes
- How it was done: Added failing Phase 10 migration contracts for direct legacy
  processing imports, rehosted processing helper modules under
  `src/dpost/application/processing/`, rewired
  `file_process_manager.py` imports to dpost modules, and validated targeted +
  full gates.

---

## Section: Record Lifecycle Rehost
- Why this matters: Record persistence guarantees are core product behavior and
  must remain stable during migration.

### Checklist
- [x] Add migration contracts for record ownership and lifecycle parity.
- [x] Introduce dpost-owned record orchestration service and storage boundary.
- [x] Rehost create/update/save/load/get flows from legacy `RecordManager`.
- [x] Preserve record upload-state and id semantics.
- [x] Remove legacy record-manager imports from canonical runtime/processing
      paths.
- [x] Verify migration and full gates are green.

### Completion Notes
- How it was done: `LocalRecord` and `RecordManager` were rehosted to
  `src/dpost/application/records/`, processing/runtime paths were rewired to
  dpost record ownership seams, and gate runs remained green.

---

## Section: Sync Core Rehost
- Why this matters: Sync behavior affects external system integrity and
  operator trust.

### Checklist
- [x] Add migration contracts for sync orchestration and error-message parity.
- [x] Rehost sync orchestration behind `SyncAdapterPort` in dpost application
      services.
- [x] Split Kadi implementation into dpost-owned infrastructure modules.
- [x] Preserve lazy optional dependency loading and startup error behavior.
- [x] Remove legacy sync manager imports except approved adapter internals.
- [x] Verify migration and full gates are green.

### Completion Notes
- How it was done: Added dpost-owned `kadi_manager` ownership seam, rewired
  `dpost.infrastructure.sync.kadi` away from direct legacy sync-manager
  imports, and validated sync/runtime migration contracts and global gates.

---

## Section: Config Runtime Rehost
- Why this matters: Runtime config lifecycle is a central dependency for all
  startup and processing behavior.

### Checklist
- [ ] Add migration contracts for config runtime ownership.
- [ ] Introduce dpost-owned config runtime lifecycle module.
- [ ] Rehost init/current/activation behavior with parity.
- [ ] Remove legacy config/storage imports from
      `src/dpost/infrastructure/runtime/config_dependencies.py`.
- [ ] Retire or reduce config dependency shim module.
- [ ] Verify migration and full gates are green.

### Completion Notes
- How it was done: Pending.

---

## Section: Shim Retirement and Import Sweep
- Why this matters: Migration completion requires deleting transition shims and
  proving canonical imports are legacy-free.

### Checklist
- [ ] Add migration contracts asserting no direct legacy core imports in
      canonical runtime modules.
- [ ] Retire `runtime_dependencies.py` once processing/records/sync are rehosted.
- [ ] Retire `config_dependencies.py` once config runtime is rehosted.
- [ ] Keep only explicitly approved legacy implementation boundaries and
      document rationale.
- [ ] Verify migration and full gates are green.

### Completion Notes
- How it was done: Pending.

---

## Section: OSS Hardening and Contributor Readiness
- Why this matters: Architecture quality is not complete until contributors can
  understand and extend the runtime cleanly.

### Checklist
- [ ] Update architecture baseline/contract/responsibility catalog to final
      ownership state.
- [ ] Update contributor-facing runtime extension docs.
- [ ] Record any policy changes as ADRs.
- [ ] Update glossary with new internal architecture terms.
- [ ] Validate docs are internally consistent and current.

### Completion Notes
- How it was done: Pending.

---

## Section: Manual Check
- Why this matters: Human workflow checks validate behavior parity that
  automated tests can miss.

### Checklist
- [ ] Desktop run check: startup, processing, rename flow, and sync errors.
- [ ] Headless run check: startup, processing, metrics, observability.
- [ ] Processing parity check: representative ACCEPT and non-ACCEPT paths.
- [ ] Record/sync parity check: persistence + immediate-sync outcomes.
- [ ] Contributor readability check: runtime flow understandable from dpost
      modules without legacy tracing.

### Manual Validation Steps
1. Run desktop mode (`DPOST_RUNTIME_MODE=desktop`) and process representative
   valid/invalid artifacts; confirm rename and sync error behavior.
2. Run headless mode (`DPOST_RUNTIME_MODE=headless`) and verify processing,
   metrics endpoint, and observability endpoints.
3. Exercise processing flows covering ACCEPT, DEFERRED, and rejected inputs.
4. Validate record creation/update and immediate-sync behaviors on
   representative datasets.
5. Review touched dpost runtime modules for readability and clear ownership.

### Completion Notes
- How it was done: Pending.
