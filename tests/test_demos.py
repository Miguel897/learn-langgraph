"""Smoke tests: run every demo as a script and check it exits cleanly.

Demos that call an LLM are marked `llm` and skipped when the configured
backend is not reachable. Run only the fast ones with:  uv run pytest -m "not llm"
"""
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

import pytest

from learn_langgraph import get_settings

DEMOS_DIR = Path(__file__).resolve().parents[1] / "demos"
NO_LLM_DEMOS = {"03_state_graph_basics.py"}
STDIN = {"07_human_in_the_loop.py": "y\n"}  # answers the approval prompt


def _backend_available() -> bool:
    s = get_settings()
    if s.llm_provider == "anthropic":
        return bool(os.getenv("ANTHROPIC_API_KEY"))
    try:
        with urllib.request.urlopen(f"{s.ollama_base_url}/api/tags", timeout=2):
            return True
    except OSError:
        return False


def _params():
    for path in sorted(DEMOS_DIR.glob("[0-9][0-9]_*.py")):
        marks = [] if path.name in NO_LLM_DEMOS else [pytest.mark.llm]
        yield pytest.param(path, id=path.stem, marks=marks)


@pytest.fixture(scope="session")
def backend_available() -> bool:
    return _backend_available()


@pytest.mark.parametrize("demo", list(_params()))
def test_demo_runs(demo: Path, request: pytest.FixtureRequest) -> None:
    if request.node.get_closest_marker("llm") and not request.getfixturevalue("backend_available"):
        pytest.skip("LLM backend not reachable")
    result = subprocess.run(
        [sys.executable, str(demo)],
        input=STDIN.get(demo.name, ""),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        timeout=600,
    )
    assert result.returncode == 0, result.stderr[-3000:]
