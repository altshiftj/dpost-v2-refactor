# Checklist: Lane A sem_phenomxl2

## Section: SEM parity tests
- Why this matters: Implementation should start from explicit SEM behavior failures.

### Checklist
- [x] Confirm `lane0-spec-lock` parity tests are available.
- [x] Run SEM parity tests red-first.
- [x] Add missing SEM-specific tests only within SEM scope if gaps remain.

### Completion Notes
- How it was done:
  - Consumed the red SEM parity target from `lane0-spec-lock` at commit `b33d33e`.
  - Ran `python -m pytest -q tests/dpost_v2/plugins/devices/sem_phenomxl2/test_parity_spec.py` red-first and confirmed `3 failed`.
  - No SEM-only test expansion was needed because `SEM001` to `SEM003` already covered the accepted parity scope.

---

## Section: SEM implementation
- Why this matters: SEM is the cleanest first plugin migration and sets the pattern for the other device lanes.

### Checklist
- [x] Implement trailing-digit normalization behavior.
- [x] Implement native image handling behavior.
- [x] Implement ELID zip or descriptor flow behavior as specified.
- [x] Keep changes inside `src/dpost_v2/plugins/devices/sem_phenomxl2/**`.

### Completion Notes
- How it was done:
  - Updated `src/dpost_v2/plugins/devices/sem_phenomxl2/settings.py` to accept `.elid` alongside native image extensions.
  - Replaced the template-only processor behavior with SEM-local processing that strips one trailing digit during `prepare()` and emits native images as `datatype="img"`.
  - Added ELID directory processing that returns a ZIP `final_path` and carries `.odt` and `.elid` descriptor artifacts through `force_paths`.

---

## Section: SEM validation
- Why this matters: Lane output is only merge-ready when the plugin behavior is proven on V2 runtime surfaces.

### Checklist
- [x] Run targeted SEM tests.
- [x] Run any SEM runtime smoke assigned to this lane.
- [x] Record risks or deferred SEM gaps.

### Completion Notes
- How it was done:
  - Ran `python -m pytest -q tests/dpost_v2/plugins/devices/sem_phenomxl2/test_parity_spec.py` and got `3 passed`.
  - Ran `python -m ruff check src/dpost_v2/plugins/devices/sem_phenomxl2 tests/dpost_v2/plugins/devices/sem_phenomxl2` and it passed.
  - No SEM-specific runtime smoke was assigned to this lane beyond the targeted parity suite.
  - Remaining risks:
    - ELID secondary artifacts are only described at the processor contract level; shared runtime/persist does not yet materialize them end-to-end.
    - Legacy descriptor dedupe/collision handling remains deferred per the parity matrix.
