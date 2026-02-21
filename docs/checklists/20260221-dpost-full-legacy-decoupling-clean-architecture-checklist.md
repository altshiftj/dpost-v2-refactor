# dpost Full Legacy Decoupling Clean-Architecture Checklist

## Section: Cross-cutting Parity Governance
- Why this matters: Full decoupling is only safe when behavior parity and
  architecture quality are enforced in every slice.

### Checklist
- [x] Define functional-equivalence assertions for each decoupling slice.
- [x] Define syntactic-simplification targets for each slice.
- [x] Block adapter retirement unless slice-specific parity tests are green.
- [x] Require architecture docs and glossary updates in each architecture
      change set.
- [x] Capture red/green evidence and residual risk in reports.

### Completion Notes
- How it was done: Enforced through migration boundary tests, red/green
  execution evidence, and architecture/report updates in each runtime
  decoupling increment.

---

## Section: Capability Audit and Mapping
- Why this matters: A complete map of legacy behavior prevents accidental
  feature loss during migration.

### Checklist
- [x] Build a capability inventory for startup, processing, plugin/config,
      records, and sync paths.
- [x] Link each legacy capability to a target `dpost` module owner.
- [ ] Mark unsupported/deprecated behavior explicitly with migration rationale.
- [x] Add migration tests for unresolved capability gaps.
- [x] Freeze the capability map as baseline before adapter deletion.

### Completion Notes
- How it was done: Inventory baseline captured in
  `docs/reports/20260221-full-legacy-decoupling-functional-architecture-audit.md`
  and linked to ownership targets in roadmap/checklist artifacts.

---

## Section: Native Runtime Bootstrap Completion
- Why this matters: Full decoupling cannot close while canonical runtime still
  executes through legacy bootstrap internals.

### Checklist
- [x] Add failing migration tests for remaining bootstrap adapter coupling.
- [x] Implement native `dpost` bootstrap service replacing legacy delegation.
- [x] Preserve startup settings/error/context semantics through parity tests.
- [x] Retire `legacy_bootstrap_adapter` from canonical runtime path.
- [x] Verify migration and full gates are green after retirement.

### Completion Notes
- How it was done: Added
  `tests/migration/test_phase13_native_bootstrap_service_retirement.py`,
  replaced canonical bootstrap delegation with native dpost implementation in
  `src/dpost/runtime/bootstrap.py`, retired
  `src/dpost/infrastructure/runtime/legacy_bootstrap_adapter.py`, and
  validated migration/lint/format/full-suite gates.

---

## Section: Plugin and Config Ownership Migration
- Why this matters: Open-source extensibility depends on plugin/config contracts
  owned by canonical `dpost` boundaries.

### Checklist
- [x] Add failing migration tests for plugin loader ownership in `dpost`.
- [x] Move plugin discovery/registration contracts to `dpost` boundaries.
- [x] Move PC-device mapping ownership to `dpost` plugin/config modules.
- [x] Preserve actionable plugin error messages and dependency hints.
- [x] Verify migration and full gates are green.

### Completion Notes
- How it was done: Added
  `tests/migration/test_phase12_plugin_loading_ownership.py`,
  implemented `src/dpost/plugins/system.py` and `src/dpost/plugins/loading.py`
  as canonical boundaries, preserved actionable unknown-plugin errors, and
  validated required gates.

---

## Section: Application Runtime and Processing Rehost
- Why this matters: Clean architecture requires runtime orchestration and
  processing behavior to live in `dpost/application` with clear ports.

### Checklist
- [x] Add failing migration tests for runtime loop ownership in
      `dpost/application`.
- [x] Rehost runtime app loop orchestration from legacy app module.
- [x] Rehost processing entry orchestration behind `dpost/application` services.
- [x] Preserve stage-order behavior, retry policy, and rejection handling.
- [x] Verify migration and full gates are green.

### Completion Notes
- How it was done: Added
  `tests/migration/test_phase10_runtime_app_rehost.py`, introduced
  `src/dpost/application/runtime/device_watchdog_app.py`, and rewired runtime
  bootstrap dependencies to use the dpost app module. Follow-up hardening
  introduced `src/dpost/application/runtime/runtime_dependencies.py`,
  `src/dpost/application/ports/interactions.py`, and
  `src/dpost/application/interactions/messages.py` so canonical runtime app
  code no longer imports legacy config/processing/session/message modules
  directly. Deep-core follow-up rehosted processing helper modules under
  `src/dpost/application/processing/` and rewired
  `file_process_manager.py` away from direct `ipat_watchdog.core.processing.*`
  imports.

---

## Section: Records and Sync Core Migration
- Why this matters: Record lifecycle and sync behavior are core product
  guarantees and must migrate without behavior drift.

### Checklist
- [x] Add failing migration tests for record manager and sync trigger ownership.
- [x] Move record lifecycle orchestration to `dpost` application/domain modules.
- [x] Keep sync behavior behind `dpost` ports and infrastructure adapters.
- [ ] Preserve immediate-sync semantics and user-visible sync error messaging.
- [x] Verify migration and full gates are green.

### Completion Notes
- How it was done: Record lifecycle ownership seams were introduced in
  `src/dpost/application/records/` and canonical processing/runtime imports now
  resolve record/sync contracts through dpost modules. Additional focused
  migration assertions for sync error-message parity remain open.

---

## Section: Legacy Runtime Retirement and OSS Hardening
- Why this matters: Full decoupling is complete only when canonical runtime is
  fully `dpost`-native and maintainable for external contributors.

### Checklist
- [x] Add failing migration tests asserting no canonical runtime dependency on
      `src/ipat_watchdog/core/...`.
- [ ] Remove remaining runtime dependency surfaces and transition-only glue.
- [ ] Finalize stable module boundaries and public extension contracts.
- [ ] Update contributor docs for architecture, testing, and extension points.
- [x] Verify migration and full gates are green.

### Completion Notes
- How it was done: Canonical startup now uses dpost-owned bootstrap/logging/
  observability paths and no longer depends on transition bootstrap adapters.
  Canonical runtime infrastructure now routes UI adapter, desktop UI, sync
  manager, and config/storage imports through dpost-owned modules. Deep-core
  follow-up rehosted processing/storage/config/metrics ownership under dpost,
  retired `runtime_dependencies.py` + `config_dependencies.py`, and moved
  desktop UI implementation into `src/dpost/infrastructure/runtime/`.
  Remaining work is final plugin-namespace/hook compatibility retirement and
  contributor-surface hardening.

---

## Section: Manual Check
- Why this matters: Human workflow verification confirms parity for operator
  behavior that automated tests can miss.

### Checklist
- [ ] Desktop manual check: startup, processing, rename flow, and sync error
      surfacing remain correct.
- [ ] Headless manual check: startup, processing, metrics, and observability
      remain correct.
- [ ] Plugin manual check: representative plugin set loads/processes across
      instrument families.
- [ ] Records/sync manual check: local persistence and sync side effects match
      expected behavior.
- [ ] Architecture readability manual check: canonical startup and runtime paths
      are understandable without legacy module tracing.

### Manual Validation Steps
1. Run desktop mode (`DPOST_RUNTIME_MODE=desktop`) and process representative
   valid/invalid artifacts; confirm rename and sync error behavior.
2. Run headless mode (`DPOST_RUNTIME_MODE=headless`) and verify startup,
   processing, metrics, and observability endpoints.
3. Execute plugin spot checks across instrument families with one failure-path
   validation for actionable error messaging.
4. Validate record persistence and sync outcomes for representative workloads.
5. Review touched runtime/composition/service modules for readability and clear
   boundary ownership.

### Completion Notes
- How it was done: Pending.
