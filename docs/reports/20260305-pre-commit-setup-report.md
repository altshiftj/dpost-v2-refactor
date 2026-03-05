# 2026-03-05 Pre-Commit Setup Report

## Summary

This slice established a reproducible local `pre-commit` setup for the active
V2 surfaces.

## Changes

- Added `pre-commit`, `pytest`, and `pyfakefs` to the `dev` optional
  dependency group in `pyproject.toml`.
- Documented local setup and hook installation in `README.md` and
  `DEVELOPER_README.md`.
- Simplified `.pre-commit-config.yaml` to match the active CI quality policy:
  Ruff plus Black, without a separate `isort` hook.
- Created a local `.venv` and installed the repo with dev dependencies.
- Installed the repository hook with `python -m pre_commit install`.
- Ran `python -m pre_commit run --all-files` successfully.

## Environment Notes

- Editable install in the fresh venv succeeded with `--no-build-isolation`.
- The existing hook set reformatted several active V2 files on first run.

## Validation

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]" --no-build-isolation
.\.venv\Scripts\python.exe -m pre_commit install
.\.venv\Scripts\python.exe -m pre_commit run --all-files
```

## Deferred

- CI still runs `black --check` and `ruff check` directly rather than invoking
  `pre-commit`. Local and CI policy now match, but the execution path is still
  separate.
