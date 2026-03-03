# Checklist: Pipeline Collaborator Hardening Slice

## Objective
- Clarify pipeline/runtime collaborator contracts so stage flow remains explicit while side-effect capabilities are exposed through stable port names.

## Section 1: Runtime Port Contract Shape
- Why this matters: contributors should understand collaborator responsibilities from method names without reading manager internals.

### Checklist
- [ ] Inventory `ProcessingPipelineRuntimePort` methods and identify manager-private name leakage.
- [ ] Propose renamed capability-style methods in the runtime port and adapter.
- [ ] Migrate pipeline calls to the new runtime capability names in small, test-backed slices.

### Completion Notes
- How it was done: _pending_

---

## Section 2: Coupling Reduction Without Behavior Drift
- Why this matters: cleanup should reduce ambiguity, not create new abstraction noise.

### Checklist
- [ ] Keep decision/order logic in `_ProcessingPipeline` (no flow shift into adapter).
- [ ] Extract micro-collaborators only when reused by multiple runtime operations.
- [ ] Confirm no change in processing status semantics (`PROCESSED`, `DEFERRED`, `REJECTED`).

### Completion Notes
- How it was done: _pending_

---

## Manual Check
- Run:
  - `python -m pytest -q tests/unit/application/processing/test_file_process_manager.py`
  - `python -m pytest -q tests/unit/application/processing/test_file_process_manager_branches.py`
  - `python -m pytest -q tests/unit/application/processing/test_record_flow.py`
  - `python -m pytest -q tests/integration/test_integration.py`
