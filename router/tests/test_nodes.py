from collections.abc import Callable, Sequence

import pytest
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage

from router.backends import Backend, BackendOutcome
from router.nodes import backend_node, score_node
from router.state import (
    BackendRefused,
    BackendUnavailable,
    Completed,
    Route,
    RouterState,
)


def initial_state(prompt: str = "hello") -> RouterState:
    return {
        "messages": [HumanMessage(content=prompt)],
        "route": None,
        "outcome": None,
        "input_tokens": 0,
        "output_tokens": 0,
        "latency_ms": 0,
    }


def returning(outcome: BackendOutcome) -> Backend:
    def backend(messages: Sequence[AnyMessage], on_chunk: Callable[[str], None]) -> BackendOutcome:
        return outcome

    return backend


@pytest.mark.parametrize(
    ("prompt", "forced_route"),
    [
        ("x" * 1_000, Route.LOCAL),
        ("what is 2+2", Route.HOSTED),
    ],
)
def test_a_forced_route_is_recorded_without_scoring(prompt: str, forced_route: Route) -> None:
    assert score_node(forced_route)(initial_state(prompt)) == {"route": forced_route}


def test_a_completed_outcome_becomes_a_state_delta() -> None:
    answer = AIMessage(content="four")
    outcome = Completed(answer, input_tokens=3, output_tokens=1)
    state = initial_state()

    delta = backend_node(returning(outcome), Route.LOCAL, lambda chunk: None)(state)

    assert delta["messages"] == [answer]
    assert delta["outcome"] == outcome
    assert delta["input_tokens"] == 3
    assert delta["output_tokens"] == 1
    assert isinstance(delta["latency_ms"], int)
    assert delta["latency_ms"] >= 0
    assert state == initial_state()


def test_an_unavailable_outcome_records_failure_without_a_message() -> None:
    outcome = BackendUnavailable("server is down")
    delta = backend_node(returning(outcome), Route.LOCAL, lambda chunk: None)(initial_state())

    assert delta["outcome"] == outcome
    assert "messages" not in delta
    assert delta["input_tokens"] == 0
    assert delta["output_tokens"] == 0


def test_a_refused_outcome_records_failure_without_a_message() -> None:
    outcome = BackendRefused("rate limited")
    delta = backend_node(returning(outcome), Route.HOSTED, lambda chunk: None)(initial_state())

    assert delta["outcome"] == outcome
    assert "messages" not in delta
    assert delta["input_tokens"] == 0
    assert delta["output_tokens"] == 0
