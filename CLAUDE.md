# CLAUDE.md

Learning playground for LangGraph 1.x / LangChain 1.x. Python 3.14, managed with `uv`.

## Commands
- `uv sync` — install deps (incl. dev group with pytest)
- `uv run demos/NN_name.py` — run a demo
- `uv run pytest -m "not llm"` — fast tests (no LLM needed)
- `uv run pytest` — full suite; runs every demo as a subprocess (~1.5 min on local Ollama)

## Layout
- `src/learn_langgraph/` — shared helpers imported by every demo. Always get models via
  `get_chat_model()` / `get_embeddings()` so the `.env` provider switch (`LLM_PROVIDER=ollama|anthropic`) keeps working.
- `demos/NN_*.py` — numbered lessons, basic → advanced. Each is a standalone script with a
  docstring explaining its concepts; graph demos call `save_mermaid()` (output in `demos/output/`, git-ignored).
  `demos/mcp_server.py` is a helper MCP server for demo 14, not a lesson (unnumbered, so tests skip it).
- `tests/test_demos.py` — auto-discovers `demos/[0-9][0-9]_*.py`. A new demo is marked `llm`
  unless it is added to `NO_LLM_DEMOS`; demos that read stdin need an entry in `STDIN`.

## Conventions
- Default local model is `qwen3:4b-instruct` on a 4 GB GPU: keep prompts short and tasks simple
  enough for a small model; context window is `OLLAMA_NUM_CTX=4096`.
- Ollama runs in Docker (`docker start ollama`, port 11434). Demo 08 always uses Ollama embeddings.
- New demos: next number, module docstring with an ASCII diagram + "Concepts" list, use `header()` for sections,
  and update the tree in `README.md`.
