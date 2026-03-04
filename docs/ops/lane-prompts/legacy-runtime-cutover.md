You are working in D:\Repos\d-post\.worktrees\legacy-runtime-cutover.

Lane: legacy-runtime-cutover
Worktree mode (mandatory):
- Run all commands, edits, and commits from this lane worktree path only.
- Do not run lane implementation work from D:\Repos\d-post root checkout.
Autonomy mode (mandatory):
- Execute fully autonomously until the lane task is complete.
- Do not ask for human input during normal implementation flow.
- Only stop/ask if hard-blocked by missing credentials, unavailable required external systems, or contradictory instructions.

Goal:
Finalize runtime cutover to V2-only behavior while keeping the CLI command name `dpost`.

Context decisions (locked):
- Command name is retained: `dpost`.
- Legacy runtime modes `v1` and `shadow` are retired.

Allowed edits:
- src/dpost_v2/__main__.py
- tests/dpost_v2/test___main__.py
- tests/dpost_v2/application/startup/**

Task:
- Remove/retire `v1` and `shadow` execution paths from V2 entry behavior.
- Keep deterministic CLI behavior and exit-code semantics.
- Preserve `dpost` command compatibility through V2 entry expectations.

TDD protocol (mandatory):
1. Write/update failing tests for retired-mode behavior and V2-only startup flow.
2. Implement minimal runtime-entry changes.
3. Refactor while preserving startup contracts.

Constraints:
- Do not edit outside allowed scope.
- Keep user-facing startup errors explicit and stable.

Output:
- Files changed
- Tests added/updated
- Commands run and results
- Risks/assumptions
