# Contributing to dpost

## Ground Rules

- Follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
- Keep changes focused and reviewable.
- Preserve architecture boundaries in `docs/architecture/`.
- Keep docs/tooling aligned with V2-only runtime ownership.

## Development Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,ci]"
```

## Run Quality Checks

```powershell
python -m ruff check src/dpost_v2 tests/dpost_v2
python -m black --check src/dpost_v2 tests/dpost_v2
python -m pytest -q tests/dpost_v2
```

Optional CI-subset parity checks:

```powershell
python -m pytest -q tests/dpost_v2/application/ingestion/test_pipeline_integration.py tests/dpost_v2/plugins/test_device_integration.py tests/dpost_v2/smoke
python -m pytest -q tests/dpost_v2/application/startup/test_bootstrap.py tests/dpost_v2/smoke/test_bootstrap_harness_smoke.py
```

## Pull Request Expectations

- Include a clear summary of what changed and why.
- Add or update tests for behavior changes.
- Keep docs in sync when behavior/architecture/setup changes.
- Do not bundle unrelated refactors with feature/bug-fix changes.

## Commit Guidelines

- Use concise, scoped commit messages.
- Prefer small checkpoints over large mixed commits.

## Reporting Issues

- Use GitHub Issues for bugs/regressions/feature requests.
- For security-sensitive issues, follow [SECURITY.md](SECURITY.md).

## License

By contributing, you agree your contributions are under the
[MIT License](LICENSE).
