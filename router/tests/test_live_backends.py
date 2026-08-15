import os
from pathlib import Path

import pytest
from langchain_core.messages import HumanMessage

from router.__main__ import DEFAULTS, load_dotenv
from router.backends import hosted_backend, local_backend
from router.state import Completed


@pytest.mark.live
def test_live_local_backend_streams_a_nonempty_completion() -> None:
    load_dotenv(Path(__file__).parents[1] / ".env", os.environ)
    chunks: list[str] = []
    backend = local_backend(
        os.environ.get("OLLAMA_BASE_URL", DEFAULTS["OLLAMA_BASE_URL"]),
        os.environ.get("ROUTER_LOCAL_MODEL", DEFAULTS["ROUTER_LOCAL_MODEL"]),
    )

    outcome = backend([HumanMessage(content="Reply with the number four.")], chunks.append)

    assert isinstance(outcome, Completed)
    assert outcome.output_tokens > 0
    assert chunks


@pytest.mark.live
def test_live_hosted_backend_streams_a_nonempty_completion() -> None:
    load_dotenv(Path(__file__).parents[1] / ".env", os.environ)
    chunks: list[str] = []
    backend = hosted_backend(
        os.environ.get("ROUTER_HOSTED_MODEL", DEFAULTS["ROUTER_HOSTED_MODEL"]),
        os.environ.get("ANTHROPIC_API_KEY"),
    )

    outcome = backend([HumanMessage(content="Reply with the number four.")], chunks.append)

    assert isinstance(outcome, Completed)
    assert outcome.output_tokens > 0
    assert chunks
