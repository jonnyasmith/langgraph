import argparse
import os
import sys
from collections.abc import Mapping, MutableMapping, Sequence
from pathlib import Path
from typing import TextIO, assert_never

from langchain_core.messages import HumanMessage

from router.backends import MissingCredentialError, hosted_backend, local_backend
from router.graph import build_graph
from router.state import (
    BackendRefused,
    BackendUnavailable,
    Completed,
    Route,
    RouterState,
)

DEFAULTS = {
    "OLLAMA_BASE_URL": "http://localhost:11434",
    "ROUTER_LOCAL_MODEL": "llama3.1:8b",
    "ROUTER_HOSTED_MODEL": "claude-sonnet-5",
}
_DOTENV_PATH = Path(__file__).resolve().parents[2] / ".env"


def load_dotenv(path: Path, environ: MutableMapping[str, str]) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if separator and key.strip():
            environ.setdefault(key.strip(), value.strip())


def read_prompt(argument: str | None, stdin: TextIO) -> str | None:
    if argument:
        return argument
    if stdin.isatty():
        return None
    prompt = stdin.read()
    return prompt if prompt.strip() else None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m router",
        description="Route a prompt to a local or hosted language model.",
    )
    parser.add_argument("prompt", nargs="?", help="prompt text; reads stdin when omitted")
    parser.add_argument(
        "--force",
        choices=tuple(Route),
        type=Route,
        help="bypass scoring and route to the selected backend",
    )
    parser.add_argument(
        "--metrics",
        action="store_true",
        help="print route, token counts, and latency to stderr",
    )
    return parser


def _initial_state(prompt: str) -> RouterState:
    return {
        "messages": [HumanMessage(content=prompt)],
        "route": None,
        "outcome": None,
        "input_tokens": 0,
        "output_tokens": 0,
        "latency_ms": 0,
    }


def render_result(
    result: Mapping[str, object],
    stderr: TextIO,
    *,
    metrics: bool,
    forced: bool,
) -> int:
    route = result.get("route")
    outcome = result.get("outcome")
    if not isinstance(route, Route):
        raise RuntimeError("graph result did not contain a route")
    if not isinstance(outcome, Completed | BackendUnavailable | BackendRefused):
        raise RuntimeError("graph result did not contain an outcome")

    match outcome:
        case BackendUnavailable(detail):
            print(f"{route} backend unavailable: {detail}", file=stderr)
            return 1
        case BackendRefused(detail):
            print(f"{route} backend refused: {detail}", file=stderr)
            return 1
        case Completed():
            pass
        case _ as unreachable:
            assert_never(unreachable)

    if metrics:
        input_tokens = result.get("input_tokens")
        output_tokens = result.get("output_tokens")
        latency_ms = result.get("latency_ms")
        if not all(isinstance(value, int) for value in (input_tokens, output_tokens, latency_ms)):
            raise RuntimeError("graph result contained malformed metrics")
        forced_label = " forced" if forced else ""
        print(
            f"route={route}{forced_label} input_tokens={input_tokens} "
            f"output_tokens={output_tokens} latency_ms={latency_ms}",
            file=stderr,
        )
    return 0


def main(
    argv: Sequence[str] | None = None,
    *,
    stdin: TextIO = sys.stdin,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
    environ: MutableMapping[str, str] = os.environ,
) -> int:
    parser = _parser()
    arguments = parser.parse_args(argv)
    prompt = read_prompt(arguments.prompt, stdin)
    if prompt is None:
        parser.print_usage(stderr)
        print("python -m router: error: a prompt argument or piped stdin is required", file=stderr)
        return 2

    load_dotenv(_DOTENV_PATH, environ)
    local = local_backend(
        environ.get("OLLAMA_BASE_URL", DEFAULTS["OLLAMA_BASE_URL"]),
        environ.get("ROUTER_LOCAL_MODEL", DEFAULTS["ROUTER_LOCAL_MODEL"]),
    )
    hosted = hosted_backend(
        environ.get("ROUTER_HOSTED_MODEL", DEFAULTS["ROUTER_HOSTED_MODEL"]),
        environ.get("ANTHROPIC_API_KEY"),
    )

    def emit(chunk: str) -> None:
        print(chunk, end="", file=stdout, flush=True)

    graph = build_graph(local, hosted, emit, arguments.force)
    try:
        result = graph.invoke(_initial_state(prompt))
    except MissingCredentialError as error:
        print(str(error), file=stderr)
        return 1
    return render_result(
        result,
        stderr,
        metrics=arguments.metrics,
        forced=arguments.force is not None,
    )


if __name__ == "__main__":
    raise SystemExit(main())
