# Checklist: Lane B utm_zwick

## Section: Zwick parity tests
- Why this matters: Zwick behavior is stateful and needs precise red tests before code changes begin.

### Checklist
- [x] Confirm `lane0-spec-lock` parity tests are available.
- [x] Run Zwick parity tests red-first.
- [x] Add missing Zwick-specific tests only within Zwick scope if gaps remain.

### Completion Notes
- How it was done:
  - Consumed the red Zwick parity target from `lane0-spec-lock` at commit `b33d33e`.
  - Ran `python -m pytest -q tests/dpost_v2/plugins/devices/utm_zwick/test_parity_spec.py` red-first and confirmed the original failures.
  - Added `UTM004` and `UTM005` inside `tests/dpost_v2/plugins/devices/utm_zwick/test_parity_spec.py` to lock staged gating behavior without crossing into shared runtime surfaces.

---

## Section: Zwick implementation
- Why this matters: Zwick validates staged multi-file state in V2 without reopening legacy runtime patterns.

### Checklist
- [x] Implement `.zs2` plus sentinel `.xlsx` series handling.
- [ ] Implement TTL or flush behavior.
- [ ] Implement unique move semantics and overwrite protection.
- [x] Keep changes inside `src/dpost_v2/plugins/devices/utm_zwick/**`.

### Completion Notes
- How it was done:
  - Replaced the template processor with plugin-local staged series state keyed by exact stem.
  - `.zs2` inputs now stage raw state, matching `.xlsx` inputs become processable, and finalized results emit `datatype="xlsx"` with both raw and results paths in `force_paths`.
  - TTL/session-end flush and routed unique-path allocation remain deferred because the current V2 shared seam still lacks a first-class deferred/flush contract and routed record-directory state.

---

## Section: Zwick validation
- Why this matters: Merge-ready Zwick work needs deterministic repeated-run behavior.

### Checklist
- [x] Run targeted Zwick tests.
- [x] Run any Zwick integration or runtime smoke assigned to this lane.
- [x] Record risks or deferred Zwick gaps.

### Completion Notes
- How it was done:
  - Ran `python -m pytest -q tests/dpost_v2/plugins/devices/utm_zwick/test_parity_spec.py` and got `5 passed`.
  - Ran `python -m pytest -q tests/dpost_v2/plugins/devices/utm_zwick` and got `5 passed`.
  - Ran `python -m ruff check src/dpost_v2/plugins/devices/utm_zwick tests/dpost_v2/plugins/devices/utm_zwick` and it passed.
  - No lane-specific runtime smoke was assigned beyond the plugin test scope.
  - Remaining risks:
    - TTL/session-end flush for raw-only `.zs2` series is still deferred.
    - Unique move semantics and overwrite protection are still deferred.
    - Staged state is in-memory only until a shared deferred outcome exists.
