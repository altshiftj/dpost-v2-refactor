# Checklist: V2 Legacy Cleanup Closeout

## Objective
- Close the V2 migration cleanup safely by freezing legacy usage, finalizing integration, cleaning lane operations, restoring governance controls, and starting stabilization work.

## Reference Set
- `docs/ops/lane-prompts/legacy-cleanup-4-launch-pack.md`
- `docs/planning/20260303-v2-cleanroom-rewrite-blueprint-rpc.md`
- `docs/planning/20260303-v1-to-v2-exhaustive-file-mapping-rpc.md`

## Section: Freeze Legacy Usage Policy
- Why this matters: policy lock prevents accidental reintroduction of retired `v1/shadow` behavior and legacy source/test ownership.

### Checklist
- [x] Confirmed `src/dpost/**` is retired from active runtime ownership.
- [x] Confirmed legacy test trees are retired (`tests/unit/**`, `tests/integration/**`, `tests/manual/**`, `tests/helpers/**`).
- [ ] Confirmed non-archive active docs no longer require legacy source/test paths.
- [ ] Confirmed legacy references are kept only as historical context under `docs/**/archive/**`.

### Manual Check
- [x] `rg --files src/dpost tests/unit tests/integration tests/manual tests/helpers`
- [x] `rg -n "src/dpost/|tests/unit|tests/integration|tests/manual|tests/helpers" docs --glob '!**/archive/**'`

### Completion Notes
- [x] `src/dpost` is reduced to bridge-only surfaces (`src/dpost/__init__.py`, `src/dpost/__main__.py`) and legacy tracked test trees are retired.
- [x] Non-archive docs still include legacy-path references (not yet closed); this remains open under docs/tooling cleanup follow-through.

---

## Section: Cut Final Integration Branch Artifact
- Why this matters: a single cleanup branch minimizes merge complexity and provides one auditable PR artifact.

### Checklist
- [x] Set `rewrite/v2-lane-legacy-cleanup` as the only cleanup integration branch.
- [x] Merged lane branches into `rewrite/v2-lane-legacy-cleanup`.
- [x] Stopped lane-specific behavior changes after merge except blocker fixes.

### Manual Check
- [x] `git switch rewrite/v2-lane-legacy-cleanup`
- [x] `git log --oneline --decorate -n 20`
- [x] `git branch --contains <lane-tip-sha>`

### Completion Notes
- [x] `rewrite/v2-lane-legacy-cleanup` includes merges from `legacy-runtime-cutover`, `legacy-code-retirement`, `legacy-tests-retirement`, and `legacy-docs-tooling`.
- [x] Integration head currently: `441a991`.

---

## Section: Remove Operational Debt
- Why this matters: removing stale branches/worktrees reduces operator mistakes and keeps lane tooling predictable.

### Checklist
- [x] Deleted merged lane branches on remote.
- [x] Deleted merged lane branches locally.
- [x] Removed stale local worktrees for completed lanes.
- [ ] Kept only active branches/worktrees (`main` + next work lanes).

### Manual Check
- [x] `git branch`
- [x] `git worktree list`
- [x] `git push origin --delete <merged-lane-branch>`
- [x] `git branch -d <merged-lane-branch>`
- [x] `git worktree remove <path-to-stale-worktree>`

### Completion Notes
- [x] Removed merged cleanup wave branches (`legacy-runtime-cutover`, `legacy-code-retirement`, `legacy-tests-retirement`, `legacy-docs-tooling`) from local and remote.
- [x] Removed corresponding cleanup wave worktrees under `.worktrees/`.
- [x] Older pre-cleanup lane branches/worktrees still exist and need explicit retirement decision before checking the final item.

---

## Section: Re-Tighten Repo Controls
- Why this matters: temporary relaxed controls are acceptable during migration, but long-term stability needs restored guardrails.

### Checklist
- [ ] Re-enabled branch protection/rulesets for `main`.
- [ ] Kept required CI checks enabled on `main`.
- [ ] Set approval policy for solo mode (approvals optional, checks required).
- [ ] Re-verified direct push behavior to `main` is blocked when expected.

### Manual Check
- [ ] GitHub UI: Settings -> Rulesets / Branches -> `main`
- [ ] `git push origin main` (expect rejection if protection blocks direct push)

### Completion Notes
- [ ] Pending

---

## Section: Update Source-of-Truth Docs
- Why this matters: active docs must describe the active system (`dpost_v2`) to avoid reintroducing legacy implementation paths.

### Checklist
- [ ] Top-level docs point to `src/dpost_v2` and `tests/dpost_v2`.
- [ ] Runbooks and ops prompts reflect V2-only workflow.
- [ ] Historical migration material is archived and clearly marked.

### Manual Check
- [ ] `rg -n "src/dpost/|tests/unit|tests/integration|tests/manual" README.md DEVELOPER_README.md CONTRIBUTING.md AGENTS.md docs --glob '!**/archive/**'`
- [ ] `rg -n "src/dpost_v2|tests/dpost_v2" README.md DEVELOPER_README.md CONTRIBUTING.md AGENTS.md docs`

### Completion Notes
- [ ] Pending

---

## Section: Start Post-Cleanup Stabilization Wave
- Why this matters: after structural retirement, value shifts to reliability, observability, and performance hardening.

### Checklist
- [ ] Opened stabilization planning doc/checklist for next wave.
- [ ] Scoped hardening focus areas (runtime resilience, performance, observability, CI signal quality).
- [ ] Explicitly deferred further structural deletion unless blocker-driven.

### Manual Check
- [ ] Created/updated planning artifact under `docs/planning/` or `docs/checklists/`.
- [ ] `git status --short` shows only intended stabilization planning changes.

### Completion Notes
- [ ] Pending
