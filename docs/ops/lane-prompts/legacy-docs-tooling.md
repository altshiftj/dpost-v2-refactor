You are working in D:\Repos\d-post\.worktrees\legacy-docs-tooling.

Lane: legacy-docs-tooling
Worktree mode (mandatory):
- Run all commands, edits, and commits from this lane worktree path only.
- Do not run lane implementation work from D:\Repos\d-post root checkout.
Autonomy mode (mandatory):
- Execute fully autonomously until the lane task is complete.
- Do not ask for human input during normal implementation flow.
- Only stop/ask if hard-blocked by missing credentials, unavailable required external systems, or contradictory instructions.

Goal:
Align docs and tooling with post-retirement V2-only architecture.

Context decisions (locked):
- Command name is retained: `dpost`.
- Legacy runtime modes `v1` and `shadow` are retired.

Allowed edits:
- pyproject.toml
- README.md
- DEVELOPER_README.md
- CONTRIBUTING.md
- AGENTS.md
- GLOSSARY.csv
- .github/workflows/public-ci.yml
- .github/workflows/rewrite-ci.yml
- docs/**

Task:
- Remove/update references to legacy `src/dpost` runtime and legacy test lanes.
- Keep architecture and runbooks consistent with active V2 paths.
- Keep CI/tooling docs aligned with actual workflows and active checks.

Constraints:
- Do not edit runtime code or tests outside allowed scope.
- Archive content may remain as historical record when clearly marked archive.

Output:
- Files changed
- Docs/tooling behavior changes
- Commands run and results
- Risks/assumptions
