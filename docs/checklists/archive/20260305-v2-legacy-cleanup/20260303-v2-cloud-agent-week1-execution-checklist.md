# Checklist: V2 Cloud-Agent Week-1 Execution

## Archive Status
- Historical migration execution checklist retained for planning traceability.
- Legacy runtime/test references in this file are not active V2 runtime policy.

## Section: Hosting and Governance Baseline
- Why this matters: cloud-agent parallelization needs enforceable merge policies and auditable automation boundaries.

### Checklist
- [ ] Repository is hosted on GitHub under the target org/account.
- [ ] `main` branch protection is enabled with required checks.
- [ ] Merge queue is enabled for protected branch.
- [ ] Bot/app credentials are configured with least privilege.
- [ ] PR and issue templates for lane ownership are committed.

### Completion Notes
- How it was done: pending.

---

## Section: Contract Freeze and Compatibility
- Why this matters: contract drift is the main failure mode when multiple agents implement in parallel.

### Checklist
- [ ] `RuntimeContext`, stage result model, and core ports are merged first.
- [ ] Compatibility tests fail on contract schema drift.
- [ ] A contract owner is explicitly assigned for Day 1 to Day 3.
- [ ] Contract freeze window is communicated to all lanes.

### Completion Notes
- How it was done: pending.

---

## Section: Lane Decomposition and Ownership
- Why this matters: lane overlap causes merge conflicts and invalidates velocity gains from cloud agents.

### Checklist
- [ ] Lane A created for contracts and typing.
- [ ] Lane B created for stage engine.
- [ ] Lane C created for storage adapter and migrations.
- [ ] Lane D created for sync adapter surface.
- [ ] Lane E created for plugin host and validators.
- [ ] Lane F created for parity harness and corpus.
- [ ] Lane G created for CI and observability.
- [ ] Each lane has a definition of done and test scope.

### Completion Notes
- How it was done: pending.

---

## Section: CI Gate Activation
- Why this matters: fast feedback and hard merge rules prevent low-quality parallel output from accumulating.

### Checklist
- [ ] Quick gate (<10 min) is required for all PRs.
- [ ] Integration gate is required for merges to `rewrite/v2`.
- [ ] Nightly deep gate runs parity replay and failure-injection tests.
- [ ] Contract-compatibility failures block merges.
- [ ] Parity threshold failures block merges.

### Completion Notes
- How it was done: pending.

---

## Section: Seven-Day Sprint Execution
- Why this matters: time-boxed rewrite efforts fail without explicit day-level milestones and checkpoint decisions.

### Checklist
- [ ] Day 0 setup complete (ADR, protections, templates).
- [ ] Day 1 contract freeze complete.
- [ ] Day 2 kernel skeleton complete.
- [ ] Day 3 parity harness online.
- [ ] Day 4 vertical slice (`resolve -> route -> persist`) online.
- [ ] Day 5 adapter hardening and parity delta burn-down complete.
- [ ] Day 6 shadow validation report published.
- [ ] Day 7 checkpoint decision recorded.

### Completion Notes
- How it was done: pending.

---

## Section: Manual Check
- Why this matters: dashboard and branch policies can appear configured but still fail at execution time.

### Checklist
- [ ] Open GitHub branch settings and confirm required checks and merge queue are active.
- [ ] Open at least one merged lane PR and confirm contract tests and parity subset checks passed.
- [ ] Run `python -m pytest -q tests/unit` locally on `rewrite/v2` and verify green state.
- [ ] Review parity dashboard artifact and verify threshold status is explicit.

### Completion Notes
- How it was done: pending.
