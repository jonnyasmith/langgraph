from router.state import Route

_LENGTH_BUCKET = 200
_CODE_FENCE_WEIGHT = 2
_REASONING_WEIGHT = 2
_HOSTED_THRESHOLD = 3
_REASONING_KEYWORDS = (
    "analyse",
    "compare",
    "refactor",
    "design",
    "explain why",
    "step by step",
)


def route_for(prompt: str) -> Route:
    normalized = prompt.casefold()
    length_score = (len(prompt) + _LENGTH_BUCKET - 1) // _LENGTH_BUCKET
    code_score = _CODE_FENCE_WEIGHT if "```" in prompt else 0
    reasoning_score = (
        _REASONING_WEIGHT if any(keyword in normalized for keyword in _REASONING_KEYWORDS) else 0
    )
    score = length_score + code_score + reasoning_score
    return Route.HOSTED if score >= _HOSTED_THRESHOLD else Route.LOCAL
