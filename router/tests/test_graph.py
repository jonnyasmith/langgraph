from collections.abc import Callable, Sequence

import pytest
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage

from router.backends import Backend, BackendOutcome
from router.graph import build_graph
from router.state import Completed, Route, RouterState


def initial_state(prompt: str) -> RouterState:
    return {
        "messages": [HumanMessage(content=prompt)],
        "route": None,
        "outcome": None,
        "input_tokens": 0,
        "output_tokens": 0,
        "latency_ms": 0,
    }


def recording_backend(name: str, calls: list[str]) -> Backend:
    def backend(messages: Sequence[AnyMessage], on_chunk: Callable[[str], None]) -> BackendOutcome:
        calls.append(name)
        on_chunk(name)
        return Completed(AIMessage(content=name), 1, 1)

    return backend


@pytest.mark.parametrize(
    ("prompt", "expected_route"),
    [("what is 2+2", Route.LOCAL), ("x" * 401, Route.HOSTED)],
)
def test_the_compiled_graph_routes_to_exactly_one_backend(
    prompt: str, expected_route: Route
) -> None:
    calls: list[str] = []
    chunks: list[str] = []
    graph = build_graph(
        recording_backend("local", calls),
        recording_backend("hosted", calls),
        chunks.append,
    )

    result = graph.invoke(initial_state(prompt))

    assert result["route"] is expected_route
    assert calls == [expected_route.value]
    assert chunks == [expected_route.value]
    assert isinstance(result["outcome"], Completed)
