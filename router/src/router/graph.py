from collections.abc import Callable

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from router.backends import Backend
from router.nodes import hosted_node, local_node, score_node
from router.state import Route, RouterState


def selected_route(state: RouterState) -> Route:
    route = state["route"]
    if route is None:
        raise RuntimeError("route must be selected before traversing the conditional edge")
    return route


def build_graph(
    local: Backend,
    hosted: Backend,
    on_chunk: Callable[[str], None],
    forced_route: Route | None = None,
) -> CompiledStateGraph[RouterState, None, RouterState, RouterState]:
    builder = StateGraph(RouterState)
    builder.add_node("score", score_node(forced_route))
    builder.add_node("local", local_node(local, on_chunk))
    builder.add_node("hosted", hosted_node(hosted, on_chunk))
    builder.add_edge(START, "score")
    builder.add_conditional_edges(
        "score",
        selected_route,
        {Route.LOCAL: "local", Route.HOSTED: "hosted"},
    )
    builder.add_edge("local", END)
    builder.add_edge("hosted", END)
    return builder.compile()
