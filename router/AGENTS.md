# Router Instructions

## Routing — read only what the task needs, when it needs it

### This context

- Router architecture → ARCHITECTURE.md
- Router vocabulary → docs/agents/domain.md
- Router decisions → docs/adr/
- Router coding standards → docs/CODING_STANDARDS.md

## Verification

Run from `router/`. There is no task runner and there must not be one.

- MUST run `uv run ruff format .` before verification.
- MUST run `uv run ruff check .`.
- MUST run `uv run mypy`.
- MUST run `uv run pytest`.
- MUST keep the default test run offline: it passes with no API key present and no local model served.
- MUST mark any test that calls a model `live`; those run only under `uv run pytest -m live`, which needs a served local model or a real key and costs money.
- MUST keep the graph testable without a model: routing functions and reducers are unit-tested directly, with model calls injected as fakes.
- MUST keep development tools in the `dev` dependency group, never in `project.dependencies`.
- MUST commit `uv.lock`.
- MUST NOT add a task runner, a `setup.cfg`, or a second tool-configuration file — `pyproject.toml` holds all of it.
