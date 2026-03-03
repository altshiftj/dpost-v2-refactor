# RPC: V2 Cloud-Agent Week-1 Roadmap

## Date
- 2026-03-03

## Status
- Draft for Review

## Goal
- Use cloud agents to deliver a credible V2 candidate in 7 days:
  - contracts + kernel,
  - parity harness,
  - one vertical slice,
  - shadow/differential validation.

## Non-Goals
- No full production cutover in week 1.
- No V1 retirement in week 1.
- No broad behavior changes outside V1 parity intent.

## Why This Matters
- Parallel cloud execution only works when work is decomposed by ownership with hard integration gates.
- Without strict gating, velocity creates integration debt and false progress.

## Prerequisites
1. Hosting and governance
- Repository hosted on GitHub.
- Protected `main` with required checks.
- Merge queue enabled.

2. CI baseline
- `public-ci.yml` active and green.
- Differential parity job scaffold added.

3. Security baseline
- Bot credentials scoped to PR creation and workflow execution.
- No plaintext secrets in repo.

## Cloud-Agent Operating Model
1. Human lead role
- Contract freeze authority.
- Daily integration decisions.
- Final merge authority for critical lanes.

2. Agent lanes (parallel)
- Lane A: contracts and typing.
- Lane B: stage engine.
- Lane C: storage adapter and migrations.
- Lane D: sync adapter surface.
- Lane E: plugin host/validators.
- Lane F: parity harness and corpus.
- Lane G: CI, branch rules, and observability.

3. Branching and merge policy
- `main`: protected, release-quality only.
- `rewrite/v2`: integration trunk for week-1 sprint.
- lane branches: `rewrite/v2-lane-*`.
- Merge order: contracts -> parity harness -> vertical slice adapters.

## CI Gate Spec
1. Quick gate (required on every PR)
- Ruff + Black checks.
- Affected unit tests.
- Contract compatibility tests.
- Max runtime target: 10 minutes.

2. Integration gate (required on merge to `rewrite/v2`)
- Full unit tests for V2 package.
- Deterministic vertical-slice tests.
- Differential parity subset.

3. Nightly deep gate
- Extended parity corpus replay.
- Failure-injection suite.
- Performance drift smoke check.

4. Merge-blocking policy
- Any contract schema break fails unless contract-owner approval is present.
- Any parity regression beyond threshold fails merge.

## Seven-Day Plan
1. Day 0 (Setup)
- Publish ADR for rewrite sprint activation.
- Enable branch protection and merge queue.
- Create lane issue templates and PR templates.

2. Day 1 (Contract Freeze)
- Land `RuntimeContext`, stage result model, and core port protocols.
- Freeze contract hashes and publish compatibility checks.

3. Day 2 (Kernel Skeleton)
- Land ingestion stage runner and no-op stage sequence.
- Add contract tests for each stage boundary.

4. Day 3 (Parity Harness)
- Capture V1 golden corpus.
- Land differential runner and CI parity subset job.

5. Day 4 (Vertical Slice Build)
- Implement `resolve -> route -> persist` slice in V2.
- Validate deterministic behavior against corpus subset.

6. Day 5 (Adapter Hardening)
- Add storage robustness and sync port stub behavior.
- Address top parity deltas from Day 4.

7. Day 6 (Shadow Validation)
- Run V2 in shadow mode against replayed artifacts.
- Publish unresolved gap report and risk posture.

8. Day 7 (Checkpoint Decision)
- Decide: continue sprint, hold for hardening, or stop.
- Produce signed checkpoint report with objective metrics.

## Definition of Done (Week 1)
- Contracts are frozen and enforced in CI.
- Differential parity harness is online.
- One full V2 vertical slice is green and parity-checked.
- Integration trunk is stable for two consecutive deep-gate runs.

## Metrics
- PR median cycle time by lane.
- Quick-gate and integration-gate pass rates.
- Parity pass rate and top delta categories.
- Open blocker count and time-to-resolution.

## Risks and Mitigations
1. Parallel merge collisions
- Mitigation: strict lane ownership and merge queue ordering.

2. Ambiguous task boundaries
- Mitigation: issue templates with explicit input/output contract.

3. Agent-generated low-signal diffs
- Mitigation: PR size guardrails and contract-first review.

## Rollback and Safety
- V1 remains operational source of truth during week-1 sprint.
- No release cutover from `rewrite/v2` without explicit follow-up approval.

## References
- `docs/planning/20260303-v2-cleanroom-rewrite-blueprint-rpc.md`
- `docs/planning/archive/20260303-legacy-seams-freshness-rpc.md`
- `docs/reports/20260303-v2-cloud-agent-week1-feasibility-report.md`
- `docs/checklists/20260303-v2-cloud-agent-week1-execution-checklist.md`

