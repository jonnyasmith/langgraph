# gatekeeper

Infrastructure agent that plans container deployments and stops for human approval.

The agent drafts a deployment plan, then hits `interrupt()` before any destructive terminal command. State is checkpointed to disk, so the process can exit entirely and the run resumes later from `Command(resume=...)` carrying the approval decision. Nothing blocks a thread while it waits.

## Features (planned)

- Checkpointer-backed persistence (`MemorySaver`, then Postgres)
- `interrupt()` before destructive side effects
- Resume via `Command(resume=...)`
- Dehydrate and rehydrate across process restarts
- Approval, rejection, and edit-then-approve paths

## Status

Not implemented.

## Requirements

- Python (version pinned when a `pyproject.toml` is added)
- Container runtime access for the deployment commands
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
uv run python -m gatekeeper
```
