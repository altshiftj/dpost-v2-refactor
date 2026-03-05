# Checklist: Lane 0 Spec Lock

## Section: Legacy reference extraction
- Why this matters: The plugin lanes need a shared factual reference for expected behavior.

### Checklist
- [ ] Review `src/ipat_watchdog/device_plugins/sem_phenomxl2/**`.
- [ ] Review `src/ipat_watchdog/device_plugins/utm_zwick/**`.
- [ ] Review `src/ipat_watchdog/device_plugins/psa_horiba/**`.
- [ ] Extract accepted and ambiguous behaviors separately.

### Completion Notes
- How it was done:

---

## Section: Parity-spec tests
- Why this matters: Parallel plugin work should start from failing tests, not prose alone.

### Checklist
- [ ] Add red parity-spec tests for `sem_phenomxl2`.
- [ ] Add red parity-spec tests for `utm_zwick`.
- [ ] Add red parity-spec tests for `psa_horiba`.
- [ ] Ensure each test id can be traced back to one legacy behavior statement.

### Completion Notes
- How it was done:

---

## Section: Behavior matrix publication
- Why this matters: Plugin lanes need a single visible map of required versus deferred behavior.

### Checklist
- [ ] Publish a parity matrix in `docs/checklists/`.
- [ ] Record accepted/deferred behavior per plugin.
- [ ] Hand off stable test ids to plugin lanes.

### Completion Notes
- How it was done:
