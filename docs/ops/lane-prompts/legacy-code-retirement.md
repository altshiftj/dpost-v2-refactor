You are working in D:\Repos\d-post\.worktrees\legacy-code-retirement.

Lane: legacy-code-retirement
Worktree mode (mandatory):
- Run all commands, edits, and commits from this lane worktree path only.
- Do not run lane implementation work from D:\Repos\d-post root checkout.
Autonomy mode (mandatory):
- Execute fully autonomously until the lane task is complete.
- Do not ask for human input during normal implementation flow.
- Only stop/ask if hard-blocked by missing credentials, unavailable required external systems, or contradictory instructions.

Goal:
Retire legacy canonical implementation code now superseded by V2.

Context decisions (locked):
- Command name remains `dpost`.
- Legacy runtime modes `v1` and `shadow` are retired.

Allowed edits:
- src/dpost/**
- src/__init__.py

Task:
- Remove legacy `src/dpost` implementation tree in controlled commits.
- Keep the repository build/import state coherent after removal.
- Do not add compatibility shims unless strictly required to keep V2 running.

TDD protocol (mandatory):
1. Add/update tests only if required to lock removal behavior.
2. Implement minimal deletion/refactor changes.
3. Refactor remaining references for clarity.

Constraints:
- Do not edit outside allowed scope.
- Avoid speculative rewrites; focus on safe retirement.

Output:
- Files changed
- Tests added/updated
- Commands run and results
- Risks/assumptions
