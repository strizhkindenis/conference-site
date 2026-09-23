# Repository guide

## Overview

This repository is a FastAPI student-conference website backed by SQLite and
SQLModel. Application code lives in `src/`; Jinja templates are in
`src/templates/`. Alembic manages database migrations. The project uses `uv`
for Python versions, dependencies, and command execution.

## Linting and formatting

Development tools are declared in `pyproject.toml` and locked in `uv.lock`.

- **Python linting:** Ruff, configured under `[tool.ruff.lint]`.
- **Python formatting:** Ruff Format, using the configured 79-character line
  length. Ruff is the canonical formatter; Black is present as a development
  dependency but is not the repository's formatting command.
- **Jinja linting and formatting:** djLint, configured under `[tool.djlint]`.
  The repository currently ignores djLint rules `H006` and `H013`.

Run commands from the repository root:

```console
uv run ruff check .
uv run ruff format --check .
uv run djlint src/templates --check
```

To apply formatting:

```console
uv run ruff format .
uv run djlint src/templates --reformat
```

Use `uv sync --dev` first if the development environment is not installed.
Run Ruff on Python source and djLint on Jinja templates when reviewing
changes in those areas.
