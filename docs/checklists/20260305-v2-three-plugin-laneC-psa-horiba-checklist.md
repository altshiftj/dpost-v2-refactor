# Checklist: Lane C psa_horiba

## Section: PSA parity tests
- Why this matters: PSA staged pairing behavior is broad enough that coding before red tests will drift.

### Checklist
- [ ] Confirm `lane0-spec-lock` parity tests are available.
- [ ] Run PSA parity tests red-first.
- [ ] Add missing PSA-specific tests only within PSA scope if gaps remain.

### Completion Notes
- How it was done:

---

## Section: PSA implementation
- Why this matters: PSA is the best final plugin lane once the simpler SEM and staged Zwick patterns are already proven.

### Checklist
- [ ] Implement bucketed pairing behavior.
- [ ] Implement staged flush and sequence naming behavior.
- [ ] Implement zip behavior and stale purge behavior.
- [ ] Keep changes inside `src/dpost_v2/plugins/devices/psa_horiba/**`.

### Completion Notes
- How it was done:

---

## Section: PSA validation
- Why this matters: Merge-ready PSA work needs deterministic staging outcomes and clear residual-risk notes.

### Checklist
- [ ] Run targeted PSA tests.
- [ ] Run any PSA integration or runtime smoke assigned to this lane.
- [ ] Record risks or deferred PSA gaps.

### Completion Notes
- How it was done:
