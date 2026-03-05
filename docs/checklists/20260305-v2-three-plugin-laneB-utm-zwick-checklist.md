# Checklist: Lane B utm_zwick

## Section: Zwick parity tests
- Why this matters: Zwick behavior is stateful and needs precise red tests before code changes begin.

### Checklist
- [ ] Confirm `lane0-spec-lock` parity tests are available.
- [ ] Run Zwick parity tests red-first.
- [ ] Add missing Zwick-specific tests only within Zwick scope if gaps remain.

### Completion Notes
- How it was done:

---

## Section: Zwick implementation
- Why this matters: Zwick validates staged multi-file state in V2 without reopening legacy runtime patterns.

### Checklist
- [ ] Implement `.zs2` plus sentinel `.xlsx` series handling.
- [ ] Implement TTL or flush behavior.
- [ ] Implement unique move semantics and overwrite protection.
- [ ] Keep changes inside `src/dpost_v2/plugins/devices/utm_zwick/**`.

### Completion Notes
- How it was done:

---

## Section: Zwick validation
- Why this matters: Merge-ready Zwick work needs deterministic repeated-run behavior.

### Checklist
- [ ] Run targeted Zwick tests.
- [ ] Run any Zwick integration or runtime smoke assigned to this lane.
- [ ] Record risks or deferred Zwick gaps.

### Completion Notes
- How it was done:
