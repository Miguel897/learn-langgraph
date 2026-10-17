"""Helpers to watch graphs run and to visualise their structure."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from langchain_core.messages import BaseMessage

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "demos" / "output"


def header(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def print_messages_stream(graph: Any, inputs: Any, config: dict | None = None) -> dict:
    """Stream a messages-based graph with stream_mode="values" and pretty-print
    each new message. Returns the final state."""
    state: dict = {}
    seen = 0
    if config and getattr(graph, "checkpointer", None):
        # Skip messages from earlier turns already stored for this thread.
        seen = len(graph.get_state(config).values.get("messages", []))
    for state in graph.stream(inputs, config, stream_mode="values"):
        messages: list[BaseMessage] = state.get("messages", [])
        for msg in messages[seen:]:
            msg.pretty_print()
        seen = len(messages)
    return state


def save_mermaid(graph: Any, name: str) -> Path:
    """Write the compiled graph as a Mermaid diagram (.mmd). Paste it into
    https://mermaid.live or a Markdown file to see it rendered."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{name}.mmd"
    path.write_text(graph.get_graph().draw_mermaid(), encoding="utf-8")
    print(f"[graph diagram saved to {path.relative_to(OUTPUT_DIR.parents[1])}]")
    return path
