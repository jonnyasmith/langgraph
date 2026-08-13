# builder

Modular pipeline that generates and refines SvelteKit components through a subgraph.

A parent graph handles the architecture request and decides which components are needed. Generation, linting, and refinement of the Svelte files happen inside a compiled subgraph with its own private `TypedDict`. The parent never sees the subgraph's scratch state — only the finished component payload comes back.

## Features (planned)

- Compiled subgraph nested inside a parent graph
- Private subgraph state, isolated from the parent schema
- Generate → lint → refine loop per component
- Subgraph testable on its own, without the parent
- SvelteKit component files written to disk

## Status

Not implemented.

## Requirements

- Python (version pinned when a `pyproject.toml` is added)
- Node.js and a SvelteKit target project for the lint step
- An API key for the model, via `.env`

## Setup

```bash
uv sync
```

## Test

```bash
uv run pytest
```

## Run

```bash
uv run python -m builder
```
