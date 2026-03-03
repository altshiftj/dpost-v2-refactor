# Report: V2 Cloud-Agent Rewrite Week-1 Feasibility

## Date
- 2026-03-03

## Scope
- Assess whether a cloud-agent implementation model can deliver a meaningful V2 rewrite milestone within one week.
- Define realistic week-1 output vs non-realistic expectations.

## Existing Baseline
- V2 intent and boundaries are documented:
  - `docs/planning/20260303-v2-cleanroom-rewrite-blueprint-rpc.md`
- Legacy-seam posture is documented and controlled:
  - `docs/planning/20260303-legacy-seams-freshness-rpc.md`
- Public CI baseline exists with branch-protection payload and apply script:
  - `.github/workflows/public-ci.yml`
  - `.github/branch-protection/main.required-checks.json`
  - `scripts/github/set-main-branch-protection.ps1`

## Feasibility Assessment
- Week-1 target is feasible if the target is:
  - contracts locked,
  - parity harness online,
  - one end-to-end V2 vertical slice in shadow/differential mode.
- Week-1 full replacement is not feasible safely.
- Key success factor is strict contract freeze before parallel implementation.

## Week-1 Deliverables (Realistic)
1. Governance and control plane
- Rewrite ADR approved.
- Dedicated branch strategy and merge gates active.

2. Contract-first kernel
- `RuntimeContext`, stage contracts, stage results, port protocols implemented.

3. Behavior capture and parity harness
- Golden corpus from V1 outputs committed.
- Differential runner comparing V1 vs V2 outcomes online in CI.

4. First vertical slice
- `resolve -> route -> persist` flow implemented in V2 with deterministic tests.

5. Reporting and visibility
- Daily parity dashboard artifact (pass rate, top deltas, unresolved gaps).

## Week-1 Non-Deliverables (Do Not Promise)
- Full feature parity for all plugin/device permutations.
- Full production cutover.
- Deletion of V1 runtime paths.

## Prerequisites for Cloud-Agent Execution
1. Repository hosting
- Yes: for the proposed process, repository should be hosted on GitHub.
- Why: required checks, merge queue, branch protection, PR review gates, workflow automation, and agent orchestration are easiest and auditable there.

2. Access and controls
- Bot/app credentials with least privilege.
- Branch protection policy applied and verified.
- Environments/secrets set for CI where needed.

3. Execution policy
- Contract freeze window (first 24h).
- No direct pushes to protected branches.
- Merge queue only after gate pass.

## Risk Register (Top)
1. Contract drift under parallel edits
- Mitigation: dedicated contract-owner lane, compatibility matrix checks, and schema lock after Day 1.

2. Parity blind spots
- Mitigation: golden corpus and differential runner merged before large implementation lanes.

3. CI instability under high PR volume
- Mitigation: quick gate (<10 min) + deeper nightly parity gates.

4. Agent output inconsistency
- Mitigation: pinned task templates, ownership map, and mandatory PR checklist per lane.

## Recommendation
- Proceed with a one-week cloud-agent sprint only if success criteria are explicitly set to a controlled V2 candidate, not full replacement.
- Execute using the roadmap and checklist below:
  - `docs/planning/20260303-v2-cloud-agent-week1-roadmap.md`
  - `docs/checklists/20260303-v2-cloud-agent-week1-execution-checklist.md`
