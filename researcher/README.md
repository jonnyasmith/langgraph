# researcher

Research loop that queries web tools, grades its own findings, and searches again when they are thin.

The graph is cyclic, not a DAG. A search node calls web tools, an evaluation node decides whether the gathered evidence answers the prompt, and a conditional edge either loops back for another pass or transitions to `END`. Exit conditions are explicit and bounded, so the loop cannot spend the API budget forever.

## Features (planned)

- Conditional edges for dynamic routing
- Tool binding inside nodes
- Bounded cycles with a hard iteration ceiling
- Sufficiency grading of accumulated findings
- Deterministic transition to `END`

## Status

Not implemented.

## Requirements

- Python (version pinned when a `pyproject.toml` is added)
- An API key for the model and the web search tool, via `.env`

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
uv run python -m researcher
```
