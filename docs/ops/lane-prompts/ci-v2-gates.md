You are working in D:\Repos\d-post.

Lane: ci-v2-gates
Autonomy mode (mandatory):
- Execute fully autonomously until the lane task is complete.
- Do not ask for human input during normal implementation flow.
- Only stop/ask if hard-blocked by missing credentials, unavailable required external systems, or contradictory instructions.
Goal:
Maintain CI gates for parallel V2 implementation.

Allowed edits:
- .github/workflows/**
- docs/planning/**
- docs/reports/**

Task:
Keep rewrite branch CI lightweight and reliable, while preserving strict required checks on main.
Adjust CI as implementation coverage grows in `src/dpost_v2` and `tests/dpost_v2`.

Constraints:
- Avoid brittle expression logic.
- Keep job names stable for required checks.

Output:
- Files changed
- CI behavior changes
- Risks/assumptions

