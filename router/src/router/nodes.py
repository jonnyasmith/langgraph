from collections.abc import Callable
from time import perf_counter
from typing import Protocol, assert_never

from router.backends import Backend
from router.scoring import route_for
from router.state import (
    BackendRefused,
    BackendUnavailable,
    Completed,
    Route,
    RouterState,
    RouterStateDelta,
)


class Node(Protocol):
    def __call__(self, state: RouterState) -> RouterStateDelta: ...


def score_node(forced_route: Route | None = None) -> Node:
    def score(state: RouterState) -> RouterStateDelta:
        route = forced_route or route_for(state["messages"][-1].text)
        return {"route": route}

    return score


def backend_node(backend: Backend, route: Route, on_chunk: Callable[[str], None]) -> Node:
    def call(state: RouterState) -> RouterStateDelta:
        started = perf_counter()
        outcome = backend(state["messages"], on_chunk)
        latency_ms = round((perf_counter() - started) * 1000)

        match outcome:
            case Completed(message, input_tokens, output_tokens):
                return {
                    "messages": [message],
                    "route": route,
                    "outcome": outcome,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "latency_ms": latency_ms,
                }
            case BackendUnavailable() | BackendRefused():
                return {
                    "route": route,
                    "outcome": outcome,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "latency_ms": latency_ms,
                }
            case _ as unreachable:
                assert_never(unreachable)

    return call


def local_node(backend: Backend, on_chunk: Callable[[str], None]) -> Node:
    return backend_node(backend, Route.LOCAL, on_chunk)


def hosted_node(backend: Backend, on_chunk: Callable[[str], None]) -> Node:
    return backend_node(backend, Route.HOSTED, on_chunk)
