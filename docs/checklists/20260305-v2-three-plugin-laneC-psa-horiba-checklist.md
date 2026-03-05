# Checklist: Lane C psa_horiba

## Section: PSA parity tests
- Why this matters: PSA staged pairing behavior is broad enough that coding before red tests will drift.

### Checklist
- [x] Confirm `lane0-spec-lock` parity tests are available.
- [x] Run PSA parity tests red-first.
- [x] Add missing PSA-specific tests only within PSA scope if gaps remain.

### Completion Notes
- How it was done:
  - Consumed the red PSA parity target from `lane0-spec-lock` at commit `b33d33e`.
  - Ran `python -m pytest -q tests/dpost_v2/plugins/devices/psa_horiba/test_parity_spec.py` red-first and confirmed `4 failed`.
  - Tightened the PSA parity slice with deterministic staged-folder naming/idempotent restaging and stale pending-NGB purge coverage while staying inside PSA-local test scope.

---

## Section: PSA implementation
- Why this matters: PSA is the best final plugin lane once the simpler SEM and staged Zwick patterns are already proven.

### Checklist
- [x] Implement bucketed pairing behavior.
- [x] Implement staged flush and sequence naming behavior.
- [x] Implement zip behavior and stale purge behavior.
- [x] Keep changes inside `src/dpost_v2/plugins/devices/psa_horiba/**`.

### Completion Notes
- How it was done:
  - Replaced the template processor with a PSA-local state machine that stages FIFO NGBs, buckets CSV->NGB pairs, and finalizes on the sentinel CSV->NGB sequence.
  - Added deterministic `.__staged__NN` staging folder allocation, numbered `.csv` and `.zip` outputs, stage reconstruction, and conservative stale-state purge.
  - Updated plugin capabilities to advertise preprocess and batch support, and expanded settings to accept `.tsv` inputs.

---

## Section: PSA validation
- Why this matters: Merge-ready PSA work needs deterministic staging outcomes and clear residual-risk notes.

### Checklist
- [x] Run targeted PSA tests.
- [x] Run any PSA integration or runtime smoke assigned to this lane.
- [x] Record risks or deferred PSA gaps.

### Completion Notes
- How it was done:
  - Ran `python -m pytest -q tests/dpost_v2/plugins/devices/psa_horiba` and got `4 passed`.
  - Ran `python -m ruff check src/dpost_v2/plugins/devices/psa_horiba tests/dpost_v2/plugins/devices/psa_horiba` and it passed.
  - No lane-specific runtime smoke was assigned beyond the plugin test scope.
  - Remaining risks:
    - Shared runtime still has no first-class deferred outcome for incomplete PSA events.
    - Purge is conservative only; rename-cancel and exception-bucket handling still need shared runtime support.
    - Broader runtime/composition verification was intentionally deferred to closeout.
