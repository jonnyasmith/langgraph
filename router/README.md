# router

Deterministic LangGraph state machine that routes a prompt to the cheapest model that can answer it.

A scoring node records a route, and a conditional edge sends the prompt either to a local Ollama
model or to Anthropic. Answers stream directly to stdout. Nodes return typed state deltas; reducers
accumulate messages, token counts, and latency.

## Requirements

- Python 3.14
- [uv](https://docs.astral.sh/uv/)
- Ollama serving the configured local model for local routes
- An Anthropic API key for hosted routes only

## Setup

```bash
uv sync
cp .env.example .env
```

Configuration is read first from exported environment variables, then topped up from `router/.env`.
Exported values always win. `OLLAMA_BASE_URL` may point to a remote Ollama server.

| Variable | Default |
| --- | --- |
| `OLLAMA_BASE_URL` | `http://localhost:11434` |
| `ANTHROPIC_API_KEY` | no default; required only for hosted routes |
| `ROUTER_LOCAL_MODEL` | `llama3.1:8b` |
| `ROUTER_HOSTED_MODEL` | `claude-sonnet-5` |

## Run

```bash
uv run python -m router "what is 2+2"
echo "compare these approaches" | uv run python -m router
uv run python -m router --force hosted "what is 2+2"
uv run python -m router --metrics "what is 2+2"
```

The answer is the only stdout output. Metrics and errors go to stderr.

## Verify

```bash
uv run ruff format .
uv run ruff check .
uv run mypy
uv run pytest
```

The default test run is offline and needs neither an API key nor a served model. Real provider tests
are opt-in with `uv run pytest -m live`; they require the corresponding backend and may cost money.
