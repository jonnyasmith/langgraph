# Architecture

Deterministic state machine that routes a prompt to the cheapest model that can answer it.

**Status: designed, not implemented.** This document describes the intended structure. Nothing
under `src/router/` exists yet.

## Shape

A prompt enters the graph. A scoring node applies a heuristic and records a `Route`. A conditional
edge reads that field and sends the run to one of two backend nodes. The node streams the answer to
stdout, translates the backend outcome into a state delta, and the run ends.

```text
START ─► score ──(conditional edge on state["route"])──► local  ─► END
                                                     └─► hosted ─► END
```

One prompt per invocation. No cycles, no checkpointer, no persistence — those are the subjects of
the later apps in this solution.

## Modules

```text
src/router/
  state.py       RouterState, Route, Outcome, reducers
  scoring.py     route_for(prompt) -> Route
  backends.py    Backend, BackendOutcome, local_backend, hosted_backend
  nodes.py       score_node, local_node, hosted_node   (factories)
  graph.py       build_graph(local, hosted) -> CompiledStateGraph
  __main__.py    CLI, env, composition root
```

### `state.py`

The single rigid `TypedDict` that every node contracts against, plus the `Route` and `Outcome`
enums and unions it references.

| Field | Reducer | Written by |
| --- | --- | --- |
| `messages` | `add_messages` | backend nodes |
| `route` | replace | score node |
| `outcome` | replace | backend nodes |
| `input_tokens` | `operator.add` | backend nodes |
| `output_tokens` | `operator.add` | backend nodes |
| `latency_ms` | `operator.add` | backend nodes |

The metric reducers are redundant for a single invocation, which writes each field once. They are
declared anyway: accumulation is the reducer's job, and the declaration is what stays correct when
a retry or a second call is added.

### `scoring.py`

```python
def route_for(prompt: str) -> Route: ...
```

Three signals summed against a threshold: character length (the dominant term), presence of a code
fence, and a small keyword set implying multi-step reasoning. The weights and the threshold are
module constants — deliberately *not* part of the interface, and deliberately not configurable. A
caller learns one function and one enum; the threshold is an implementation detail that the
parametrised boundary tests pin.

The heuristic is plain Python, not a model call. This keeps the default test run offline and avoids
spending a model call to decide whether to spend a model call.

### `backends.py`

The seam. One callable `Protocol` that both providers satisfy:

```python
class Backend(Protocol):
    def __call__(
        self, messages: Sequence[AnyMessage], on_chunk: Callable[[str], None]
    ) -> BackendOutcome: ...
```

Built by factories that close over their configuration:

```python
def local_backend(base_url: str, model: str) -> Backend: ...
def hosted_backend(model: str) -> Backend: ...
```

A `Protocol` return type is correct here: a closure has no denotable concrete type, so a callable
`Protocol` is the most specific type available.

This module is the exception boundary. LangChain and the provider SDKs signal expected failures as
exceptions; `backends.py` catches them and returns variants instead:

- `Completed(message, input_tokens, output_tokens)`
- `BackendUnavailable(detail)` — Ollama not served, network failure
- `BackendRefused(detail)` — rate limit, overload, provider refusal

The boundary closes with a final `except Exception` mapping to `BackendRefused`. This is a
deliberate call: an interactive CLI should not print a raw provider traceback. The cost is that a
bug in our own code inside the boundary is disguised as a provider problem, so the `try` wraps the
provider call and nothing else.

`backends.py` knows nothing about `RouterState`.

### `nodes.py`

Node factories, so the graph can close over real backends while tests close over fakes:

```python
def score_node() -> Callable[[RouterState], dict[str, object]]: ...
def local_node(backend: Backend) -> Callable[[RouterState], dict[str, object]]: ...
def hosted_node(backend: Backend) -> Callable[[RouterState], dict[str, object]]: ...
```

Injection is through the closure rather than through `config["configurable"]`, which would be
untyped at exactly the seam where nodes meet their dependencies.

This module owns the translation from outcome to state delta: the `match` over the three variants
closed with `assert_never`, the latency measurement around the backend call, and the choice of
which keys the node writes. `local_node` and `hosted_node` are one implementation with two
bindings that differ only in the injected backend and the `route` value — duplicating the match
block would hollow the module out.

Nodes are pure: they read state, they return a delta, they never assign into the state argument.
Streaming chunks to stdout is a side effect on the terminal, not on state.

### `graph.py`

```python
def build_graph(local: Backend, hosted: Backend) -> CompiledStateGraph: ...
```

Topology only: register the three nodes, add the conditional edge from `score`, wire both backend
nodes to `END`, compile with no checkpointer. The edge function is a one-line read of
`state["route"]` — a pure function of state, so it is unit-testable without a model, and every path
reaches `END`.

### `__main__.py`

The composition root, and the one module permitted to create dependencies rather than accept them.
It parses arguments, reads the environment, builds both backends, calls `build_graph`, runs it, and
renders the result.

```bash
uv run python -m router "prompt"        # prompt as argument
echo "prompt" | uv run python -m router # prompt from stdin
uv run python -m router --force hosted "prompt"
uv run python -m router --metrics "prompt"
```

The answer streams to stdout. `--metrics` prints route and token counts to **stderr**, so stdout
stays pipeable.

There is no `config.py`. A module whose whole job is reading three environment variables is a
pass-through, and the composition root is where that reading belongs.

## Configuration

| Variable | Purpose |
| --- | --- |
| `OLLAMA_BASE_URL` | Where the local model is served |
| `ANTHROPIC_API_KEY` | Hosted backend credential |
| `ROUTER_LOCAL_MODEL` | Local model name |
| `ROUTER_HOSTED_MODEL` | Hosted model name |

A missing API key `raise`s rather than becoming an outcome variant — it is an unrecoverable state,
not an expected failure. It is detected *after* routing, so a run that routes local works with no
hosted key present.

## Failure model

There is no fallback edge. A backend failure is recorded as an `outcome` variant and the run
proceeds to `END`. Falling back from local to hosted would be a second conditional edge that
silently spends money; if it is ever wanted, it should be an explicit flag.

## Testing

The default run is offline and needs no key and no served model. Model-calling tests are marked
`live`.

| Surface | What it tests | How |
| --- | --- | --- |
| `scoring.route_for` | Threshold behaviour, boundary cases | Direct calls, parametrised over inputs |
| `nodes.*_node` | Outcome-to-delta translation, including both failure variants | Fake `Backend` returning each variant |
| `build_graph` | Wiring — short prompts reach local, long prompts reach hosted | Two fake backends, assert on final state |
| `backends.*` | Real provider calls | Marked `live` |

A fake `Backend` is the whole test seam. Returning `BackendUnavailable` from a fake is far cheaper
than arranging a dead Ollama.

## Decisions worth knowing

- **Routing is a conditional edge, not a branch inside one node.** The branch is the thing this app
  exists to demonstrate, so it belongs in the topology where it is visible. The later researcher app
  differs by having a *cycle*, not by having its first conditional edge.
- **The scorer is a heuristic, not a classifier model.** Deterministic, free, and testable offline.
- **`nodes.py` is kept as its own module** rather than folded into `graph.py`. It follows the
  conventional LangGraph layout, and it earns the file by owning the outcome translation. The cost
  is two public test surfaces instead of one.
- **No cost-in-dollars metric.** It would mean hardcoding a price table that goes stale.
