from collections.abc import Iterator, Sequence

import anthropic
import httpx
import ollama
import pytest
from langchain_core.messages import AIMessageChunk, AnyMessage, HumanMessage

import router.backends as backends
from router.state import BackendRefused, BackendUnavailable


class RaisingModel:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def stream(self, messages: Sequence[AnyMessage]) -> Iterator[AIMessageChunk]:
        raise self.error
        yield


MESSAGES = [HumanMessage(content="hello")]


@pytest.mark.parametrize(
    ("error", "expected_type"),
    [
        (ollama.RequestError("cannot connect"), BackendUnavailable),
        (ConnectionError("Failed to connect to Ollama"), BackendUnavailable),
        (ollama.ResponseError("overloaded", 503), BackendRefused),
        (httpx.ReadTimeout("timed out"), BackendUnavailable),
    ],
)
def test_local_provider_exceptions_become_outcomes(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    expected_type: type[BackendUnavailable] | type[BackendRefused],
) -> None:
    monkeypatch.setattr(backends, "ChatOllama", lambda **kwargs: RaisingModel(error))
    backend = backends.local_backend("http://localhost:11434", "local")
    outcome = backend(MESSAGES, lambda chunk: None)

    assert isinstance(outcome, expected_type)
    assert outcome.detail


@pytest.mark.parametrize(
    ("error", "expected_type"),
    [
        (
            anthropic.APIConnectionError(
                request=httpx.Request("POST", "https://api.anthropic.com")
            ),
            BackendUnavailable,
        ),
        (
            anthropic.RateLimitError(
                "rate limited",
                response=httpx.Response(
                    429,
                    request=httpx.Request("POST", "https://api.anthropic.com"),
                ),
                body=None,
            ),
            BackendRefused,
        ),
        (
            anthropic.APIStatusError(
                "overloaded",
                response=httpx.Response(
                    529,
                    request=httpx.Request("POST", "https://api.anthropic.com"),
                ),
                body=None,
            ),
            BackendRefused,
        ),
    ],
)
def test_hosted_provider_exceptions_become_outcomes(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    expected_type: type[BackendUnavailable] | type[BackendRefused],
) -> None:
    monkeypatch.setattr(backends, "ChatAnthropic", lambda **kwargs: RaisingModel(error))
    backend = backends.hosted_backend("hosted", "key")
    outcome = backend(MESSAGES, lambda chunk: None)

    assert isinstance(outcome, expected_type)
    assert outcome.detail


def test_a_missing_hosted_credential_raises_before_provider_translation() -> None:
    backend = backends.hosted_backend("claude", None)

    with pytest.raises(backends.MissingCredentialError, match="ANTHROPIC_API_KEY"):
        backend(MESSAGES, lambda chunk: None)
