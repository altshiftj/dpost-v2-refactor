# Checklist: V2 PC/Device Runtime Wiring

## Section: Baseline lock
- Why this matters: Freeze known-good startup and plugin-contract behavior before runtime wiring.

### Checklist
- [ ] Confirm branch is `rewrite/v2-manual-pc-device-bringup` and working tree is clean.
- [ ] Re-run manual bring-up baseline from [20260305-v2-manual-pc-device-bringup-checklist.md](d:/Repos/d-post/docs/checklists/20260305-v2-manual-pc-device-bringup-checklist.md).
- [ ] Capture baseline command outputs in this checklist completion notes.

### Completion Notes
- How it was done:

---

## Section: Runtime execution contract (TDD)
- Why this matters: Prevent regression where startup succeeds but runtime ingestion never runs.

### Checklist
- [ ] Add failing tests for non-dry-run runtime execution path in `tests/dpost_v2/test___main__.py`.
- [ ] Add failing tests for dry-run path to confirm runtime loop is not executed.
- [ ] Implement minimal entry/bootstrap wiring changes to make tests pass.

### Completion Notes
- How it was done:

---

## Section: Real ingestion engine composition
- Why this matters: Replace noop runtime behavior with real staged ingestion execution.

### Checklist
- [ ] Add failing composition/runtime tests proving real ingestion engine wiring is used.
- [ ] Implement minimal changes in `src/dpost_v2/runtime/composition.py` to compose real ingestion engine and handlers.
- [ ] Keep stage boundaries and contract validation stable while making tests pass.
- [ ] Ensure composition preserves responsibility split: PC plugin sets workstation/device scope; sync backend handles outbound transport.

### Completion Notes
- How it was done:

---

## Section: Deterministic headless event source
- Why this matters: Manual runtime verification requires predictable non-UI input behavior.

### Checklist
- [ ] Add failing runtime tests for deterministic headless event-source handling.
- [ ] Implement minimal event-source wiring to process at least one deterministic event/file path.
- [ ] Verify non-dry-run headless mode processes expected input and exits deterministically.

### Completion Notes
- How it was done:

---

## Section: Plugin pair processing proof
- Why this matters: Confirms runtime can execute a concrete device/PC pair path, not only startup contracts.

### Checklist
- [ ] Validate runtime path with `horiba_blb` as workstation policy owner for allowed devices.
- [ ] Validate runtime path with `psa_horiba` device plugin through processor `prepare/can_process/process` under that PC scope.
- [ ] Validate PC payload-shaping behavior independently from sync transport backend behavior.
- [ ] Record final manual command outputs and artifact effects (processed path, emitted payloads, sync backend behavior).

### Completion Notes
- How it was done:

---

## Section: Validation gates and closeout
- Why this matters: Ensures runtime wiring is stable and ready for broader stabilization work.

### Checklist
- [ ] Run `python -m ruff check src/dpost_v2 tests/dpost_v2`.
- [ ] Run targeted suites: `tests/dpost_v2/test___main__.py`, `tests/dpost_v2/runtime`, `tests/dpost_v2/application/runtime`, `tests/dpost_v2/application/ingestion`, and plugin integration tests.
- [ ] Run `python -m pytest -q tests/dpost_v2` and document final status, risks, and deferred items.

### Completion Notes
- How it was done:
