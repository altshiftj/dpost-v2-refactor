# RPC: V2 Codex-GitHub Parallelization Runbook

## Date
- 2026-03-03

## Status
- Draft for Review (smoke-test note)

## Goal
- Provide one operator runbook for:
  1. setting up Codex + GitHub for parallel V2 work,
  2. orchestrating multiple models with clear chunk ownership and low merge friction.

## Why This Matters
- Parallel model execution fails when setup and ownership are vague.
- This runbook makes setup, lane instructions, and merge gates explicit and repeatable.

## Canonical Inputs
- [V2 cleanroom blueprint](./20260303-v2-cleanroom-rewrite-blueprint-rpc.md)
- [V1 to V2 exhaustive mapping](./20260303-v1-to-v2-exhaustive-file-mapping-rpc.md)
- [Pseudocode README](../pseudocode/README.md)
- [Pseudocode module specs](../pseudocode/)
- [Public CI workflow](../../.github/workflows/public-ci.yml)
- [Required checks config](../../.github/branch-protection/main.required-checks.json)

## Part 1: Operator Setup (Codex + GitHub)

### 1. Repository and Access Baseline
1. Ensure `D:\Repos\d-post` is pushed to GitHub and visible to your Codex-connected account.
2. Confirm default branch is `main`.
3. Confirm repository permissions:
- You have admin/maintain access.
- Codex integration identity has at least PR + branch workflow permissions.

### 2. Connect Codex to GitHub
1. In Codex settings, open GitHub integration.
2. Authorize GitHub account.
3. Grant access to the `d-post` repository (repo-level scope only if possible).
4. Verify Codex can:
- read repository files,
- create a branch,
- open a PR.
5. Run a smoke test: ask Codex to create a docs-only branch and PR changing one markdown line, then confirm the PR appears in GitHub with CI checks attached.

### 3. Enable and Verify CI
1. Confirm workflow exists:
- `.github/workflows/public-ci.yml`
2. Trigger one manual run (`workflow_dispatch`) from GitHub Actions.
3. Ensure required checks from `.github/branch-protection/main.required-checks.json` are green at least once.

### 4. Apply Branch Protection (Terminal-Ready)
1. Set token:
```powershell
$env:GITHUB_TOKEN="<token-with-repo-admin-scope>"
```
2. Apply policy:
```powershell
python -m pip install --upgrade pip
powershell -File scripts/github/set-main-branch-protection.ps1 -Repository "<owner>/<repo>"
```
3. Verify in GitHub UI:
- required checks enabled,
- stale reviews dismissed on new commits,
- direct push to `main` blocked.

### 5. Branch Model
- `main`: protected, release quality.
- `rewrite/v2`: integration trunk for V2.
- `rewrite/v2-lane-<lane-name>-<short-topic>`: model execution branches.

### 6. Branch Bootstrap (Terminal-Ready)
Use this once to create trunk + lane branches for parallel execution.

```powershell
git checkout main
git pull --ff-only origin main
git checkout -B rewrite/v2
git push -u origin rewrite/v2

$lanes = @(
  "rewrite/v2-lane-contracts-interfaces",
  "rewrite/v2-lane-startup-bootstrap",
  "rewrite/v2-lane-domain-core-models",
  "rewrite/v2-lane-ingestion-pipeline",
  "rewrite/v2-lane-infrastructure-adapters",
  "rewrite/v2-lane-plugins-device-system",
  "rewrite/v2-lane-runtime-composition",
  "rewrite/v2-lane-docs-pseudocode-traceability",
  "rewrite/v2-lane-tests-v2-harness",
  "rewrite/v2-lane-ci-v2-gates"
)

foreach ($lane in $lanes) {
  git checkout rewrite/v2
  git checkout -B $lane
  git push -u origin $lane
}

git checkout rewrite/v2
```

### 7. Lane Catalog (Autonomous Parallel Agents)
- `rewrite/v2-lane-contracts-interfaces`: contracts and cross-lane interface surfaces.
- `rewrite/v2-lane-startup-bootstrap`: startup sequence and bootstrap orchestration.
- `rewrite/v2-lane-domain-core-models`: domain models and pure business semantics.
- `rewrite/v2-lane-ingestion-pipeline`: ingestion and processing orchestration stages.
- `rewrite/v2-lane-infrastructure-adapters`: infrastructure adapters and side-effect boundaries.
- `rewrite/v2-lane-plugins-device-system`: plugin host/discovery plus device plugin integration points.
- `rewrite/v2-lane-runtime-composition`: runtime composition and dependency wiring.
- `rewrite/v2-lane-docs-pseudocode-traceability`: pseudocode/spec traceability and docs consistency.
- `rewrite/v2-lane-tests-v2-harness`: V2-specific test harnesses and deterministic fixtures.
- `rewrite/v2-lane-ci-v2-gates`: CI workflows/check gates scoped to V2 execution paths.

## Part 2: Model-Orchestration Contract

### 1. Lane Ownership (No Overlap Rule)
- `Contracts-Core`: `application/contracts/**`
- `Domain-Core`: `domain/**`
- `Processing-Kernel`: `application/ingestion/**`
- `Records-Core`: `application/records/**` + record behavior contracts
- `Infra-Storage`: `infrastructure/storage/**`
- `Infra-Sync`: `infrastructure/sync/**`
- `Infra-UI`: `infrastructure/runtime/ui/**`
- `Infra-Observability`: `infrastructure/observability/**`
- `Plugin-Host`: `plugins/{host,discovery,catalog,profile_selection,contracts}.py`
- `Plugin-Device-*`: one device family per lane
- `Plugin-PC-*`: one PC family per lane
- `Startup-Core`: `runtime/**` + `application/startup/**` + composition wiring

Rule: one PR = one lane. Cross-lane edits are disallowed unless contract-owner approval is explicit in the PR.

### 2. Task Chunk Size
- Target 3-8 files changed per chunk.
- Target 1 coherent behavior or contract slice per chunk.
- Avoid "mega-PR" behavior across multiple lanes.

### 3. Required Input Packet for Every Model
- `lane`: ownership lane name.
- `scope_files`: exact files allowed to edit.
- `depends_on`: contract files/specs the lane must respect.
- `pseudocode_specs`: exact `docs/pseudocode/**` files to implement from.
- `acceptance_tests`: exact tests to add/run.
- `done_definition`: measurable exit conditions.

## Part 3: Copy/Paste Model Prompt Template

```text
You are implementing a bounded V2 slice in D:\Repos\d-post.

Lane: <lane-name>
Allowed edit scope:
- <file-or-glob-1>
- <file-or-glob-2>

Do not edit outside scope.

Canonical specs:
- <docs/pseudocode/path-1>
- <docs/pseudocode/path-2>

Planning references:
- [V2 cleanroom blueprint](./20260303-v2-cleanroom-rewrite-blueprint-rpc.md)
- [V1 to V2 exhaustive mapping](./20260303-v1-to-v2-exhaustive-file-mapping-rpc.md)

Implementation task:
- <single concrete task>

Acceptance criteria:
1. <criterion>
2. <criterion>

TDD requirements:
1. Add or update failing tests first.
2. Implement to green.
3. Refactor while green.

Validation commands:
- python -m ruff check <target-paths>
- python -m pytest -q <target-tests>

Output requirements:
- summary of changes
- tests run and results
- risks/assumptions
```

## Part 4: Merge and Stitch Protocol

### 1. Merge Order
1. `Contracts-Core`
2. `Domain-Core`
3. `Processing-Kernel` + `Records-Core`
4. `Infrastructure` lanes
5. `Plugin` lanes
6. `Startup-Core`

### 2. PR Checklist (Required)
- Scope-only edits (lane ownership respected).
- Pseudocode spec alignment confirmed.
- New/updated tests included.
- `ruff` + targeted `pytest` pass.
- No forbidden imports (`ipat_watchdog.*` in `src/dpost_v2/**`).

### 3. Conflict Resolution
- If two PRs touch same contract file:
1. Pause non-owner PR.
2. Merge contract-owner PR first.
3. Rebase/replay blocked PR against new contract.

## Part 5: Orchestrator Cadence (Daily)

### Morning (30-45 min)
- Freeze/confirm today’s contract surfaces.
- Assign lane packets.
- Confirm CI health baseline.

### Midday (30 min)
- Merge quick wins.
- Resolve lane collisions.
- Re-scope blocked chunks into smaller packets.

### End of Day (45-60 min)
- Merge integration-ready PRs to `rewrite/v2`.
- Run broader validation on `rewrite/v2`.
- Publish daily status with three fields: merged lanes, blocked lanes, next-day packet queue.

## Part 6: First Wave Packet Set (Suggested)

1. Packet A (`Contracts-Core`)
- Implement contract dataclasses/protocols in `src/dpost_v2/application/contracts/*`.
- Add contract unit tests.

2. Packet B (`Domain-Core`)
- Implement naming/routing/records domain pure logic from pseudocode.
- Add deterministic domain tests.

3. Packet C (`Processing-Kernel`)
- Implement stage result model + no-op pipeline runner skeleton.
- Add stage contract tests.

4. Packet D (`Infra-Storage`)
- Implement `record_store.py` interface + fake/in-memory adapter first.
- Add repository behavior tests.

5. Packet E (`Startup-Core`)
- Implement minimal composition + bootstrap path to run no-op flow.
- Add startup smoke tests.

## Part 7: Manual Check
- Open one lane PR and verify it edited only allowed files.
- Confirm required checks execute and block failing PRs.
- Confirm pseudocode-linked implementation notes are present in PR description.
- Confirm `rewrite/v2` branch remains green after merges.

## References
- [V2 cleanroom blueprint](./20260303-v2-cleanroom-rewrite-blueprint-rpc.md)
- [V1 to V2 exhaustive mapping](./20260303-v1-to-v2-exhaustive-file-mapping-rpc.md)
- [Pseudocode README](../pseudocode/README.md)
- [Cloud agent roadmap](archive/20260303-v2-cloud-agent-week1-roadmap.md)
- [Cloud agent feasibility report](../reports/20260303-v2-cloud-agent-week1-feasibility-report.md)
- [Cloud agent execution checklist](../checklists/20260303-v2-cloud-agent-week1-execution-checklist.md)
