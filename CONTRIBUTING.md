# Contributing to dpost

Thanks for contributing to `dpost`.

## Ground Rules

- Be respectful and follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
- Keep changes focused and reviewable.
- Preserve architecture boundaries described in `docs/architecture/`.

## Development Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,ci]"
```

## Run Quality Checks

```powershell
python -m ruff check .
python -m black --check src tests
python -m pytest -q tests/unit/runtime/test_bootstrap.py tests/unit/runtime/test_bootstrap_additional.py
python -m pytest -q tests/unit
python -m pytest -q tests/integration
# Optional manual smoke lane:
python -m pytest -q -m manual tests/manual
```

## Pull Request Expectations

- Include a clear summary of what changed and why.
- Add or update tests for behavior changes.
- Keep docs in sync when behavior, architecture, or setup changes.
- Do not bundle unrelated refactors with feature or bug-fix changes.

## Commit Guidelines

- Use concise, scoped commit messages.
- Prefer small checkpoints over large mixed commits.

## Reporting Issues

- Use GitHub Issues for bugs, regressions, or feature requests.
- For security-sensitive issues, use the private reporting process in
  [SECURITY.md](SECURITY.md) and do not create a public issue.

## License

By contributing, you agree that your contributions are licensed under the
[MIT License](LICENSE).
