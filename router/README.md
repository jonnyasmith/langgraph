# router

Deterministic state machine that routes a prompt to the cheapest model that can answer it.

A prompt enters the graph, a node scores its complexity, and a static edge sends it either to a small model hosted locally on the Mac Mini or out to a larger hosted API. Every node is a pure function: it returns a state update, it never mutates state in place. Token counts and latency accumulate in the shared state via reducers.

## Features (planned)

- `StateGraph` over a rigid `TypedDict` schema
- Reducers (`add_messages`) for predictable state accumulation
- Complexity scoring node with a deterministic threshold
- Local model backend plus a hosted API backend
- Token and latency metrics recorded per run

## Status

Not implemented.

## Requirements

- Python 3.14
- [uv](https://docs.astral.sh/uv/)
- A locally served small language model (Ollama, at `OLLAMA_BASE_URL`)
- An API key for the hosted model, via `.env` — copy `.env.example`

## Setup

```bash
uv sync
```

## Test

```bash
uv run ruff format .
uv run ruff check .
uv run mypy
uv run pytest
```

The default test run is offline: it needs no API key and no served model. Tests that call a
real model are marked `live` and run only under `uv run pytest -m live`.

## Run

```bash
uv run python -m router
```
