import operator
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, AnyMessage
from langgraph.graph.message import add_messages


class Route(StrEnum):
    LOCAL = "local"
    HOSTED = "hosted"


@dataclass(frozen=True)
class Completed:
    message: AIMessage
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class BackendUnavailable:
    detail: str


@dataclass(frozen=True)
class BackendRefused:
    detail: str


Outcome = Completed | BackendUnavailable | BackendRefused


class RouterState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    route: Route | None
    outcome: Outcome | None
    input_tokens: Annotated[int, operator.add]
    output_tokens: Annotated[int, operator.add]
    latency_ms: Annotated[int, operator.add]


class RouterStateDelta(TypedDict, total=False):
    messages: list[AnyMessage]
    route: Route | None
    outcome: Outcome | None
    input_tokens: int
    output_tokens: int
    latency_ms: int
