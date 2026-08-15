from collections.abc import Callable, Iterator, Sequence
from typing import Protocol

import anthropic
import httpx
import ollama
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, AIMessageChunk, AnyMessage
from langchain_ollama import ChatOllama
from pydantic import SecretStr

from router.state import BackendRefused, BackendUnavailable, Completed

_REQUEST_TIMEOUT_SECONDS = 30.0
_HOSTED_MAX_TOKENS = 4096

BackendOutcome = Completed | BackendUnavailable | BackendRefused


class MissingCredentialError(RuntimeError):
    pass


class Backend(Protocol):
    def __call__(
        self, messages: Sequence[AnyMessage], on_chunk: Callable[[str], None]
    ) -> BackendOutcome: ...


def _collect_stream(
    stream: Callable[[Sequence[AnyMessage]], Iterator[AIMessageChunk]],
    messages: Sequence[AnyMessage],
    on_chunk: Callable[[str], None],
) -> Completed:
    aggregate: AIMessageChunk | None = None
    for chunk in stream(messages):
        text = chunk.text
        if text:
            on_chunk(text)
        aggregate = chunk if aggregate is None else aggregate + chunk

    if aggregate is None:
        return Completed(AIMessage(content=""), 0, 0)

    usage = aggregate.usage_metadata
    input_tokens = usage["input_tokens"] if usage is not None else 0
    output_tokens = usage["output_tokens"] if usage is not None else 0
    return Completed(aggregate, input_tokens, output_tokens)


def _invoke_local(
    stream: Callable[[Sequence[AnyMessage]], Iterator[AIMessageChunk]],
    messages: Sequence[AnyMessage],
    on_chunk: Callable[[str], None],
) -> BackendOutcome:
    try:
        return _collect_stream(stream, messages, on_chunk)
    except (
        ConnectionError,
        httpx.ConnectError,
        httpx.TimeoutException,
        ollama.RequestError,
    ) as error:
        return BackendUnavailable(str(error))
    except ollama.ResponseError as error:
        return BackendRefused(str(error))
    except Exception as error:
        return BackendRefused(str(error))


def _invoke_hosted(
    stream: Callable[[Sequence[AnyMessage]], Iterator[AIMessageChunk]],
    messages: Sequence[AnyMessage],
    on_chunk: Callable[[str], None],
) -> BackendOutcome:
    try:
        return _collect_stream(stream, messages, on_chunk)
    except (anthropic.APIConnectionError, anthropic.APITimeoutError) as error:
        return BackendUnavailable(str(error))
    except anthropic.APIStatusError as error:
        return BackendRefused(str(error))
    except Exception as error:
        return BackendRefused(str(error))


def local_backend(base_url: str, model: str) -> Backend:
    client = ChatOllama(
        model=model,
        base_url=base_url,
        sync_client_kwargs={"timeout": _REQUEST_TIMEOUT_SECONDS},
    )

    def stream(messages: Sequence[AnyMessage]) -> Iterator[AIMessageChunk]:
        return client.stream(messages)

    def call(messages: Sequence[AnyMessage], on_chunk: Callable[[str], None]) -> BackendOutcome:
        return _invoke_local(stream, messages, on_chunk)

    return call


def hosted_backend(model: str, api_key: str | None) -> Backend:
    client: ChatAnthropic | None = None

    def call(messages: Sequence[AnyMessage], on_chunk: Callable[[str], None]) -> BackendOutcome:
        nonlocal client
        if not api_key:
            raise MissingCredentialError("ANTHROPIC_API_KEY is required for the hosted backend")
        if client is None:
            client = ChatAnthropic(
                model_name=model,
                api_key=SecretStr(api_key),
                max_tokens_to_sample=_HOSTED_MAX_TOKENS,
                timeout=_REQUEST_TIMEOUT_SECONDS,
                stop=None,
            )
        active_client = client

        def stream(messages: Sequence[AnyMessage]) -> Iterator[AIMessageChunk]:
            return active_client.stream(messages)

        return _invoke_hosted(stream, messages, on_chunk)

    return call
