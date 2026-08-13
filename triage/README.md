# triage

Multi-agent team that triages incoming GitHub issues behind a supervisor node.

A GitHub webhook delivers a new issue. A supervisor node routes it — and only routes it — to specialist workers: project management categorises it for continuous flow, QA drafts a test plan, and architecture proposes an implementation. Independent workers run in parallel and their outputs accumulate into shared state before the supervisor closes the run.

## Features (planned)

- Supervisor topology with tight, deterministic routing
- Parallel fan-out to independent worker nodes
- Specialist workers as separately routed subgraphs
- Shared state accumulation across concurrent branches
- GitHub webhook ingestion and comment write-back

## Status

Not implemented.

## Requirements

- Python (version pinned when a `pyproject.toml` is added)
- A GitHub token and a webhook endpoint reachable from GitHub
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
uv run python -m triage
```
