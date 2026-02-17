# AI Agent Instructions (kadi_tools)

## Purpose
- This repo is a Python tooling/CLI project for Kadi-related workflows.
- Keep changes safe, small, and easy to review.

## Scope
- Prefer edits under `src/` and `tests/` (if tests exist).
- Avoid touching `.venv/`, `uv.lock`, or generated files unless asked.

## Workflow
- Inspect existing code before editing.
- Use small, targeted diffs.
- Prefer `python -m ...` invocations to avoid PATH issues on Windows.
- Avoid compatibility shims or legacy wrappers unless explicitly requested or there is
  clear, current usage that requires them.
- Follow a strict human-in-the-loop TDD cycle for novel code:
  - First, write failing tests and report back.
  - Wait for human approval to proceed.
  - Implement code to make tests pass.
  - Human verifies tests.
  - Suggest possible refactors afterward.

## Planning Phases and Docs
- When prompted to examine or plan novel functionality, maintain documentation:
  - `reports/`: findings in existing code.
  - `planning/`: plan of attack for the requested functionality.
  - `checklists/`: step-by-step checklist for the work.
- `refactors/`: post-green refactor proposals and implementation notes.
- "RPC" is shorthand for this report/plan/checklist workflow.
- Checklists must include a short "why this matters" blurb per section.
- Checklists must include a final `Manual Check` section with concrete human validation
  steps (UI/API/role-path checks as relevant).
- When a checklist section is completed, mark it done and add a short "how it was done" blurb.

## Code Style
- Python 3.12+.
- Format with Black (88 char lines).
- Lint with Ruff.
- Type checking is strict; write code to satisfy strict type checking rules and avoid
  typing shortcuts unless clearly justified.
- Add type hints for new public functions.
- Docstrings are required for all tests and functions.

## Commands
- Lint: `python -m ruff check .`
- Lint fix: `python -m ruff check . --fix`
- Format: `python -m black .`
- Tests: `python -m pytest`

## Key Files
- CLI entrypoint: `src/kadi-tools/__main__.py`
- Package directory: `src/kadi-tools` (note the hyphen).

## Output
- Summarize changes and note tests run (or say not run).
- When providing test commands, always give a full terminal-ready line that can be copy/pasted.

## Glossary
- Maintain a `GLOSSARY.csv` at the repo root for project-defined terms.
- CSV columns: `term`, `type`, `purpose`, `usage`.
- Only include terms we invent for this codebase (exclude library/vendor terms).
- When introducing a new term in code or docs, add it to the glossary.
- Before writing new code, review the glossary and use consistent terminology.
