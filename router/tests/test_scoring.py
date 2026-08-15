import pytest

from router.scoring import route_for
from router.state import Route


@pytest.mark.parametrize(
    ("length", "expected"),
    [
        (1, Route.LOCAL),
        (200, Route.LOCAL),
        (400, Route.LOCAL),
        (401, Route.HOSTED),
    ],
)
def test_prompt_length_routes_at_the_documented_threshold(length: int, expected: Route) -> None:
    assert route_for("x" * length) is expected


def test_a_code_fence_routes_to_the_hosted_model() -> None:
    assert route_for("```python\nprint('hello')\n```") is Route.HOSTED


@pytest.mark.parametrize("keyword", ["compare", "ANALYSE"])
def test_a_reasoning_keyword_routes_to_the_hosted_model(keyword: str) -> None:
    assert route_for(f"Please {keyword} these options") is Route.HOSTED


def test_individually_insufficient_signals_combine_at_the_threshold() -> None:
    assert route_for("x" * 200 + "```") is Route.HOSTED
