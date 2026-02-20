# dpost Phase 9-13 Full Strangler Checklist

## Section: Phase 9 Native dpost Bootstrap Core
- Why this matters: Removing bootstrap-level legacy coupling is the first hard
  boundary needed for a truly native `dpost` runtime.

### Checklist
- [ ] Add/confirm migration tests that fail when runtime bootstrap/composition
      depend on `ipat_watchdog.core.app.bootstrap`.
- [ ] Introduce native `dpost` bootstrap context/settings/error contract.
- [ ] Remove legacy bootstrap-module dependency from `src/dpost/runtime/bootstrap.py`.
- [ ] Remove legacy bootstrap type/module dependency from
      `src/dpost/runtime/composition.py`.
- [ ] Verify migration + full gates are green.

### Completion Notes
- How it was done: Pending.

---

## Section: Phase 10 Application Orchestration Extraction
- Why this matters: Runtime composition should orchestrate through application
  services/ports instead of legacy monolith wiring.

### Checklist
- [ ] Add failing migration tests for `dpost/application` orchestration usage.
- [ ] Extract orchestration entrypoints into `dpost/application` services.
- [ ] Keep behavior parity for processing/session runtime paths.
- [ ] Verify migration + full gates are green.

### Completion Notes
- How it was done: Pending.

---

## Section: Phase 11 Infrastructure Adapter Extraction
- Why this matters: Clean adapter boundaries prevent application logic from
  drifting back into concrete integration dependencies.

### Checklist
- [ ] Add failing migration tests for application-to-infrastructure boundary
      enforcement.
- [ ] Move runtime/filesystem/observability glue behind `dpost/infrastructure`
      adapters and ports.
- [ ] Ensure composition root owns adapter selection/wiring.
- [ ] Verify migration + full gates are green.

### Completion Notes
- How it was done: Pending.

---

## Section: Phase 12 Plugin and Config Boundary Migration
- Why this matters: Plugin/config ownership must live in `dpost` boundaries for
  long-term extensibility and open-source maintainability.

### Checklist
- [ ] Add failing migration tests for plugin/config boundary ownership in
      `dpost`.
- [ ] Migrate plugin/config startup contracts to `dpost` boundary modules.
- [ ] Keep plugin discovery errors actionable and regression-tested.
- [ ] Verify migration + full gates are green.

### Completion Notes
- How it was done: Pending.

---

## Section: Phase 13 Legacy Runtime Retirement
- Why this matters: Final strangler completion requires canonical runtime paths
  to run without legacy core runtime module dependency.

### Checklist
- [ ] Add failing migration tests asserting no runtime dependency on
      `src/ipat_watchdog/core/...` from canonical startup path.
- [ ] Remove remaining runtime dependency surfaces and transition-only glue.
- [ ] Update docs/checklists/execution board to reflect legacy runtime
      retirement completion.
- [ ] Verify migration + full gates are green.

### Completion Notes
- How it was done: Pending.

---

## Section: Manual Check
- Why this matters: Human verification confirms end-to-end runtime behavior
  after each major architectural boundary shift.

### Checklist
- [ ] Desktop manual check: startup succeeds and representative processing flow
      remains correct.
- [ ] Desktop manual check: rename, error messaging, and sync dialogs remain
      behaviorally correct.
- [ ] Headless manual check: startup/processing/observability remain functional.
- [ ] Plugin manual check: representative plugin set loads and processes across
      instrument families.
- [ ] Migration hygiene manual check: documented setup/start commands work from
      a clean environment.

### Manual Validation Steps
1. Run desktop mode (`DPOST_RUNTIME_MODE=desktop`) and validate startup,
   processing, rename-flow, and sync error surfacing behavior.
2. Run headless mode (`DPOST_RUNTIME_MODE=headless`) and validate processing,
   metrics endpoint, and optional observability endpoint behavior.
3. Execute representative plugin spot checks for each instrument family.
4. Validate documented install/run commands from README and user/developer docs
   in a clean environment.

### Completion Notes
- How it was done: Pending.
