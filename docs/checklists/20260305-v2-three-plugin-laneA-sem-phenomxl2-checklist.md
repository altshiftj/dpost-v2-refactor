# Checklist: Lane A sem_phenomxl2

## Section: SEM parity tests
- Why this matters: Implementation should start from explicit SEM behavior failures.

### Checklist
- [ ] Confirm `lane0-spec-lock` parity tests are available.
- [ ] Run SEM parity tests red-first.
- [ ] Add missing SEM-specific tests only within SEM scope if gaps remain.

### Completion Notes
- How it was done:

---

## Section: SEM implementation
- Why this matters: SEM is the cleanest first plugin migration and sets the pattern for the other device lanes.

### Checklist
- [ ] Implement trailing-digit normalization behavior.
- [ ] Implement native image handling behavior.
- [ ] Implement ELID zip or descriptor flow behavior as specified.
- [ ] Keep changes inside `src/dpost_v2/plugins/devices/sem_phenomxl2/**`.

### Completion Notes
- How it was done:

---

## Section: SEM validation
- Why this matters: Lane output is only merge-ready when the plugin behavior is proven on V2 runtime surfaces.

### Checklist
- [ ] Run targeted SEM tests.
- [ ] Run any SEM runtime smoke assigned to this lane.
- [ ] Record risks or deferred SEM gaps.

### Completion Notes
- How it was done:
