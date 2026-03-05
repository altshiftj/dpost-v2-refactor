# Checklist: Lane 0 Spec Lock

## Section: Legacy reference extraction
- Why this matters: The plugin lanes need a shared factual reference for expected behavior.

### Checklist
- [x] Review `src/ipat_watchdog/device_plugins/sem_phenomxl2/**`.
- [x] Review `src/ipat_watchdog/device_plugins/utm_zwick/**`.
- [x] Review `src/ipat_watchdog/device_plugins/psa_horiba/**`.
- [x] Extract accepted and ambiguous behaviors separately.

### Completion Notes
- How it was done:
  - Reviewed the three legacy plugin source trees plus:
    - `src/ipat_watchdog/device_plugins/psa_horiba/README.md`
    - `src/ipat_watchdog/device_plugins/utm_zwick/docs/*`
  - Cross-checked those behaviors against reference tests under:
    - `tests_legacy_reference/ipat_watchdog/tests/unit/device_plugins/**`
  - Treated legacy processor source as primary and legacy tests as secondary evidence.

---

## Section: Parity-spec tests
- Why this matters: Parallel plugin work should start from failing tests, not prose alone.

### Checklist
- [x] Add red parity-spec tests for `sem_phenomxl2`.
- [x] Add red parity-spec tests for `utm_zwick`.
- [x] Add red parity-spec tests for `psa_horiba`.
- [x] Ensure each test id can be traced back to one legacy behavior statement.

### Completion Notes
- How it was done:
  - Added red tests under:
    - `tests/dpost_v2/plugins/devices/sem_phenomxl2/test_parity_spec.py`
    - `tests/dpost_v2/plugins/devices/utm_zwick/test_parity_spec.py`
    - `tests/dpost_v2/plugins/devices/psa_horiba/test_parity_spec.py`
  - Used stable ids:
    - `SEM001` to `SEM003`
    - `UTM001` to `UTM003`
    - `PSA001` to `PSA003`
  - Added `tests/dpost_v2/plugins/devices/_helpers.py` for shared V2 processing-context setup.

---

## Section: Behavior matrix publication
- Why this matters: Plugin lanes need a single visible map of required versus deferred behavior.

### Checklist
- [x] Publish a parity matrix in `docs/checklists/`.
- [x] Record accepted/deferred behavior per plugin.
- [x] Hand off stable test ids to plugin lanes.

### Completion Notes
- How it was done:
  - Published:
    - `docs/checklists/20260305-v2-three-plugin-parity-matrix.md`
    - `docs/reports/20260305-v2-lane0-spec-lock-report.md`
  - Documented the contract-risk/deferred items separately so plugin lanes do not silently redefine shared runtime expectations.
