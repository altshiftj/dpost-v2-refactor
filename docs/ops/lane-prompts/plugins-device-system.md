You are working in D:\Repos\d-post\.worktrees\plugins-device-system.

Lane: plugins-device-system
Worktree mode (mandatory):
- Run all commands, edits, and commits from this lane worktree path only.
- Do not run lane implementation work from D:\Repos\d-post root checkout.
Autonomy mode (mandatory):
- Execute fully autonomously until the lane task is complete.
- Do not ask for human input during normal implementation flow.
- Only stop/ask if hard-blocked by missing credentials, unavailable required external systems, or contradictory instructions.
Goal:
Phase 2 (hardening + gap closure): close mapped plugin migration gaps and harden plugin host/discovery/device integration in TDD order.

Allowed edits:
- src/dpost_v2/plugins/**
- tests/dpost_v2/plugins/**

Canonical references:
- docs/pseudocode/plugins/**
- docs/planning/20260303-v2-cleanroom-rewrite-blueprint-rpc.md
- docs/planning/20260303-v1-to-v2-exhaustive-file-mapping-rpc.md

Phase focus (mandatory):
- Prioritize concrete device/pc plugin migrations listed in the V1->V2 mapping before adding new scaffolding.
- Expand edge-case coverage for discovery, selection, loading, and host lifecycle behavior.
- Treat template-only or cosmetic changes as out of scope unless required to unblock mapped migrations.

TDD protocol (mandatory):
1. Write failing tests for plugin discovery/selection/loading behavior.
2. Implement minimal plugin runtime code.
3. Refactor while keeping plugin contracts stable.

Constraints:
- Do not edit outside allowed scope.
- Keep plugin boundaries explicit.

Output:
- Files changed
- Tests added/updated
- Commands run and results
- Risks/assumptions

