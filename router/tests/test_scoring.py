import pytest

from router.scoring import route_for
from router.state import Route


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("x", Route.LOCAL),
        ("x" * 200, Route.LOCAL),
        ("x" * 400, Route.LOCAL),
        ("x" * 401, Route.HOSTED),
        ("```python\nprint('hello')\n```", Route.HOSTED),
        ("Please compare these options", Route.HOSTED),
        ("Please ANALYSE this choice", Route.HOSTED),
        ("x" * 200 + "```", Route.HOSTED),
    ],
)
def test_prompt_signals_route_at_the_documented_threshold(prompt: str, expected: Route) -> None:
    assert route_for(prompt) is expected
