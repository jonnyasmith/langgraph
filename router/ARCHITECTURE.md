# Architecture

Deterministic state machine that routes a prompt to the cheapest model that can answer it.

**Status: implemented.** The source and tests under `src/router/` and `tests/` implement this design.

## Shape

A prompt enters the graph. A scoring node applies a heuristic and records a `Route`. A conditional
edge reads that field and sends the run to one of two backend nodes. The backend node passes chunks
to an injected sink and translates the backend outcome into a state delta. The composition root owns
the real stdout sink. The run then ends.

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
  graph.py       build_graph(local, hosted, on_chunk, forced_route=None) -> CompiledStateGraph
  __main__.py    CLI, env, composition root
```

### `state.py`

`RouterState` is the single rigid, total `TypedDict` every node reads. `RouterStateDelta` is the
partial write-side `TypedDict` every node returns. `Route` is a `StrEnum`; the outcome is a named
union of `Completed`, `BackendUnavailable`, and `BackendRefused`.

The partial write type is required because `dict[str, object]` does not satisfy LangGraph's node
protocol under strict mypy. It also makes delta-only writes part of the checked contract.

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
def hosted_backend(model: str, api_key: str | None) -> Backend: ...
```

A `Protocol` return type is correct here: a closure has no denotable concrete type, so a callable
`Protocol` is the most specific type available.

This module is the exception boundary. LangChain and the provider SDKs signal expected failures as
exceptions; `backends.py` catches them and returns variants instead:

- `Completed(message, input_tokens, output_tokens)`
- `BackendUnavailable(detail)` — Ollama not served, network failure
- `BackendRefused(detail)` — rate limit, overload, provider refusal

The boundary closes with a final `except Exception` mapping to `BackendRefused`. The `try` wraps
only stream iteration. Connection errors, timeouts, and Ollama request errors become unavailable;
provider status and response errors become refused. Both clients have a 30-second request timeout.
`anthropic` and `ollama` are declared direct dependencies because this boundary catches their
exception classes by identity; relying on them transitively would leave the boundary undeclared.

The hosted client is lazy. A missing API key raises before the exception boundary, so local routes
need no key and missing credentials are never mislabeled as a provider refusal. Model clients are
not explicitly closed: the one-shot process cannot reach the wrappers' underlying clients without
depending on private APIs.

### `nodes.py`

Node factories, so the graph can close over real backends while tests close over fakes:

```python
def score_node(forced_route: Route | None = None) -> Node: ...
def local_node(backend: Backend, on_chunk: Callable[[str], None]) -> Node: ...
def hosted_node(backend: Backend, on_chunk: Callable[[str], None]) -> Node: ...
```

Injection is through the closure rather than through `config["configurable"]`, which would be
untyped at exactly the seam where nodes meet their dependencies.

This module owns the translation from outcome to state delta: the `match` over the three variants
closed with `assert_never`, the latency measurement around the backend call, and the choice of
which keys the node writes. `local_node` and `hosted_node` are one implementation with two
bindings that differ only in the injected backend and the `route` value — duplicating the match
block would hollow the module out.

Nodes are state-pure: they read state, return a delta, and never assign into the state argument.
Streaming is an explicit injected side effect. The composition root owns the stdout sink; tests
replace it with `list.append`.

### `graph.py`

```python
def build_graph(
    local: Backend,
    hosted: Backend,
    on_chunk: Callable[[str], None],
    forced_route: Route | None = None,
) -> CompiledStateGraph[RouterState, None, RouterState, RouterState]: ...
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

The answer streams to stdout. `--metrics` prints route, input and output token counts, and latency
as one line on **stderr**, so stdout stays pipeable. Forced runs are marked `forced`. Successful
runs exit 0, backend failures exit 1, and usage errors exit 2.

Configuration and `.env` loading stay in the composition root rather than a pass-through
`config.py`. The `.env` reader skips comments and blanks and never replaces an exported value.

## Configuration

| Variable | Purpose | Default |
| --- | --- | --- |
| `OLLAMA_BASE_URL` | Where the local model is served | `http://localhost:11434` |
| `ANTHROPIC_API_KEY` | Hosted backend credential | none |
| `ROUTER_LOCAL_MODEL` | Local model name | `llama3.1:8b` |
| `ROUTER_HOSTED_MODEL` | Hosted model name | `claude-sonnet-5` |

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
| `nodes.*_node` | Forced routing and outcome-to-delta translation | Fake `Backend` outcomes |
| `build_graph` | Short/long routing and exactly one backend call | Two fake backends |
| `backends.*` | Provider exception mapping | Fakes raising real exception classes |
| CLI helpers | Prompt precedence, `.env`, defaults, missing input/key | In-memory streams and mappings |
| live backends | Streaming and non-zero output tokens | Explicit `live` marker |

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
- **LangGraph 1.x constrains several type details.** Node state parameters are named `state` to
  satisfy its protocol. Nodes return the partial `RouterStateDelta`, because `dict[str, object]`
  fails strict mypy at that seam. `CompiledStateGraph` carries all four generic parameters rather
  than using a bare annotation for the same reason.
