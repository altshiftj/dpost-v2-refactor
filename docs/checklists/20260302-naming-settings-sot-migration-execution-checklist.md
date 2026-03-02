# NamingSettings Single-Source Migration Execution Checklist (2026-03-02)

## 1. Confirm Baseline and Scope
- Why this matters: locking scope up front prevents mixed migration goals and
  avoids churn across naming, storage, sync, and plugin boundaries.

### Checklist
- [x] Confirm RPC exists and is the canonical migration reference:
      `docs/planning/20260224-naming-settings-single-source-of-truth-rpc.md`.
- [x] Confirm architecture cross-links are present in baseline/contract/catalog
      docs and architecture README.
- [x] Confirm this checklist tracks only naming-source and fallback-retirement
      work (not unrelated refactors).
- [x] Decide whether runtime naming-overload file/folder renames are in-scope
      for this wave or explicitly deferred.

### Completion Notes
- How it was done: kickoff baseline cross-link verification completed on
  2026-03-02 using `rg` over `docs/architecture` and `README.md`; runtime
  naming-overload renames are explicitly deferred for this wave.

---

## 2. Retire Ambient Naming Facade Lookups
- Why this matters: `current()` fallback lookups in application naming policy
  hide dependencies and weaken explicit-context guarantees.

### Checklist
- [x] Update `src/dpost/application/naming/policy.py` so naming operations use
      explicit context without ambient fallback (`_id_separator`,
      `_filename_pattern`, `_current_device` retirement path).
- [x] Update all call sites to pass explicit naming context where required
      (`id_separator`, `filename_pattern`, device metadata).
- [x] Remove or minimize compatibility wrappers once no production path depends
      on ambient reads.
- [x] Add/adjust focused tests in:
      `tests/unit/application/naming/test_policy.py`,
      `tests/unit/application/processing/test_routing_helpers.py`,
      `tests/unit/application/processing/test_file_process_manager_branches.py`,
      `tests/unit/application/records/test_record_manager.py`.

### Completion Notes
- How it was done: replaced ambient fallback behavior in
  `application/naming/policy.py` with explicit-context validation; wired
  runtime filename-pattern injection via `configure_runtime_context(...)`;
  updated Hioki modified-event checks to require injected naming context; and
  updated affected tests to pass explicit separator/pattern context.
  Validation:
  - `python -m pytest -q tests/unit/application/naming/test_policy.py tests/unit/device_plugins/erm_hioki/test_file_processor.py tests/unit/application/processing/test_file_process_manager_branches.py tests/unit/application/processing/test_file_process_manager.py tests/unit/application/processing/test_force_paths_kadi_sync.py tests/unit/device_plugins/erm_hioki/test_live_run_sequence.py` -> `65 passed`
  - `python -m pytest -q tests/unit/application/records/test_record_manager.py tests/unit/application/processing/test_routing_helpers.py tests/unit/application/processing/test_file_process_manager_branches.py` -> `51 passed, 1 skipped`
  - `python -m ruff check ...` (touched src/tests in this slice) -> pass

---

## 3. Remove Storage Helper Ambient Defaults
- Why this matters: storage path/separator helpers should receive explicit
  policy inputs from orchestration boundaries, not active global config.

### Checklist
- [ ] Replace fallback usage in
      `src/dpost/infrastructure/storage/filesystem_utils.py` where explicit
      context is already available (`dest_dir`, `rename_dir`, `exception_dir`,
      `id_separator`, `current_device`).
- [ ] Keep dependency direction intact by passing context from application or
      runtime composition boundaries only.
- [ ] Remove residual `_active_config()`-based wrappers once call-site coverage
      is complete and tested.
- [ ] Add/adjust focused tests in:
      `tests/unit/infrastructure/storage/test_filesystem_utils.py` and related
      processing flow tests.

### Completion Notes
- How it was done:

---

## 4. Tighten Kadi Separator Policy to Explicit Behavior
- Why this matters: separator inference in sync flows can drift from canonical
  naming policy and hides missing upstream context wiring.

### Checklist
- [ ] Refactor `src/dpost/infrastructure/sync/kadi_manager.py` to rely on an
      explicit separator resolver contract rather than inference scans.
- [ ] Remove or strictly constrain `_infer_id_separator_from_record(...)` and
      default fallback behavior after separator propagation is guaranteed.
- [ ] Verify `LocalRecord` creation/update paths always provide separator
      information needed by sync operations.
- [ ] Add/adjust tests in:
      `tests/unit/infrastructure/sync/test_sync_kadi.py` and
      `tests/unit/infrastructure/sync/test_sync_kadi_branches.py`.

### Completion Notes
- How it was done:

---

## 5. Remove Plugin Runtime Separator Fallbacks
- Why this matters: plugin-local runtime fallbacks (`current()`/`"-"`) create
  hidden behavior branches and undercut constructor/runtime context injection.

### Checklist
- [ ] Update Kinexus and PSA processors to require explicit separator context
      via constructor or `configure_runtime_context(...)` before processing.
- [ ] Remove `_runtime_id_separator()` fallback and `RuntimeError -> "-"` paths
      from:
      `src/dpost/device_plugins/rhe_kinexus/file_processor.py`,
      `src/dpost/device_plugins/psa_horiba/file_processor.py`.
- [ ] Ensure runtime orchestration and processor factory paths always inject
      separator context before plugin processing starts.
- [ ] Add/adjust focused tests in:
      `tests/unit/device_plugins/rhe_kinexus/test_file_processor.py`,
      `tests/unit/device_plugins/rhe_kinexus/test_file_processor_branches.py`,
      `tests/unit/device_plugins/psa_horiba/test_file_processor.py`,
      `tests/unit/device_plugins/psa_horiba/test_file_processor_branches.py`.

### Completion Notes
- How it was done:

---

## 6. Deferred Naming-Clarity Renames (Optional Slice)
- Why this matters: naming-overload cleanup can improve readability, but it
  should not distract from explicit-context migration risk reduction.

### Checklist
- [ ] If in scope, execute low-risk rename sequence from RPC:
      `application/config/runtime.py -> application/config/context.py`,
      `infrastructure/runtime/bootstrap_dependencies.py -> startup_dependencies.py`.
- [ ] If out of scope, record defer decision in active report/checklist notes.
- [ ] Update imports/tests/docs consistently if rename slice is executed.

### Completion Notes
- How it was done:

---

## Manual Check
- Why this matters: final validation confirms fallback-retirement changes did
  not regress behavior and keeps architecture guardrails enforceable.

### Checklist
- [ ] Run:
      `python -m ruff check src/dpost/application/naming/policy.py src/dpost/infrastructure/storage/filesystem_utils.py src/dpost/infrastructure/sync/kadi_manager.py src/dpost/device_plugins/rhe_kinexus/file_processor.py src/dpost/device_plugins/psa_horiba/file_processor.py tests/unit/application/naming/test_policy.py tests/unit/infrastructure/storage/test_filesystem_utils.py tests/unit/infrastructure/sync/test_sync_kadi.py tests/unit/infrastructure/sync/test_sync_kadi_branches.py tests/unit/device_plugins/rhe_kinexus/test_file_processor.py tests/unit/device_plugins/rhe_kinexus/test_file_processor_branches.py tests/unit/device_plugins/psa_horiba/test_file_processor.py tests/unit/device_plugins/psa_horiba/test_file_processor_branches.py`
- [ ] Run:
      `python -m pytest -q tests/unit/application/naming/test_policy.py tests/unit/infrastructure/storage/test_filesystem_utils.py tests/unit/infrastructure/sync/test_sync_kadi.py tests/unit/infrastructure/sync/test_sync_kadi_branches.py tests/unit/device_plugins/rhe_kinexus/test_file_processor.py tests/unit/device_plugins/rhe_kinexus/test_file_processor_branches.py tests/unit/device_plugins/psa_horiba/test_file_processor.py tests/unit/device_plugins/psa_horiba/test_file_processor_branches.py tests/unit/application/processing/test_file_process_manager_branches.py tests/unit/application/processing/test_routing_helpers.py tests/unit/application/records/test_record_manager.py`
- [ ] Run:
      `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit`
- [ ] Run:
      `rg -n "ipat_watchdog\\." src/dpost`
- [ ] Confirm architecture docs remain aligned with final migration status and
      update this checklist/report pair with concrete command results.

## Completion Notes
- How it was done:
