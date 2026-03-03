# Checklist: Helper Signature Narrowing (Storage/Naming) Slice

## Objective
- Narrow helper signatures in storage/naming hot paths to explicit context requirements while preserving behavior through targeted compatibility seams.

## Section 1: Signature Inventory and Scope
- Why this matters: narrowing should target true high-value APIs, not create churn everywhere.

### Checklist
- [ ] Inventory storage and naming helper functions with optional context parameters.
- [ ] Classify call sites by runtime criticality (hot path vs compatibility/manual path).
- [ ] Select first narrowing subset where all production call sites already pass explicit context.

### Completion Notes
- How it was done: _pending_

---

## Section 2: Safe Narrowing Execution
- Why this matters: helper signature cleanup must not change processing outcomes.

### Checklist
- [ ] Convert selected helper signatures to required explicit args.
- [ ] Update call sites and tests in the same slice.
- [ ] Isolate any retained fallback behavior behind explicit compatibility wrappers.

### Completion Notes
- How it was done: _pending_

---

## Manual Check
- Run:
  - `python -m pytest -q tests/unit/infrastructure/storage/test_filesystem_utils.py`
  - `python -m pytest -q tests/unit/application/naming/test_policy.py`
  - `python -m pytest -q tests/unit/application/processing/test_record_persistence_context.py tests/unit/application/processing/test_rename_flow.py`
  - `python -m pytest -q tests/integration/test_integration.py`
