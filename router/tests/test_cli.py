from io import StringIO
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

import router.__main__ as cli
from router.__main__ import load_dotenv, main, read_prompt, render_result
from router.state import Completed, Route


def test_an_argument_wins_over_stdin() -> None:
    assert read_prompt("argument", StringIO("stdin")) == "argument"


def test_stdin_supplies_the_prompt_when_no_argument_exists() -> None:
    assert read_prompt(None, StringIO("piped prompt\n")) == "piped prompt\n"


def test_no_prompt_prints_usage_to_stderr_and_exits_two() -> None:
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main([], stdin=StringIO(""), stdout=stdout, stderr=stderr, environ={})

    assert exit_code == 2
    assert stdout.getvalue() == ""
    assert "usage:" in stderr.getvalue()
    assert "prompt" in stderr.getvalue()


def test_dotenv_parses_assignments_comments_and_blanks(tmp_path: Path) -> None:
    directory = tmp_path
    dotenv = directory / ".env"
    dotenv.write_text(
        "# comment\n\nOLLAMA_BASE_URL=http://remote:11434\nROUTER_LOCAL_MODEL=small\n"
    )
    environ: dict[str, str] = {}

    load_dotenv(dotenv, environ)

    assert environ == {
        "OLLAMA_BASE_URL": "http://remote:11434",
        "ROUTER_LOCAL_MODEL": "small",
    }


def test_exported_environment_values_win_over_dotenv(tmp_path: Path) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text("ROUTER_HOSTED_MODEL=from-file\n")
    environ = {"ROUTER_HOSTED_MODEL": "exported"}

    load_dotenv(dotenv, environ)

    assert environ["ROUTER_HOSTED_MODEL"] == "exported"


def test_a_hosted_route_without_a_key_is_reported_distinctly(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(cli, "_DOTENV_PATH", tmp_path / ".env")
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main(
        ["x" * 401],
        stdin=StringIO(""),
        stdout=stdout,
        stderr=stderr,
        environ={},
    )

    assert exit_code == 1
    assert stdout.getvalue() == ""
    assert stderr.getvalue() == "ANTHROPIC_API_KEY is required for the hosted backend\n"


def test_metrics_render_to_stderr_and_mark_a_forced_route() -> None:
    stderr = StringIO()
    result: dict[str, object] = {
        "route": Route.LOCAL,
        "outcome": Completed(AIMessage(content="four"), 3, 1),
        "input_tokens": 3,
        "output_tokens": 1,
        "latency_ms": 12,
    }

    exit_code = render_result(result, stderr, metrics=True, forced=True)

    assert exit_code == 0
    assert stderr.getvalue() == (
        "route=local forced input_tokens=3 output_tokens=1 latency_ms=12\n"
    )


def test_a_malformed_graph_result_raises() -> None:
    result: dict[str, object] = {"route": "not-a-route"}

    with pytest.raises(RuntimeError, match="graph result did not contain a route"):
        render_result(result, StringIO(), metrics=False, forced=False)
