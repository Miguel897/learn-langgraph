# learn-langgraph

A hands-on playground for learning **LangGraph** and **LangChain**, running on a small local model (Ollama) or on Anthropic.

```
learn-langgraph/
├── docs/
│   ├── langgraph-intro.html     # visual intro: key classes, patterns, diagrams (open in a browser)
│   └── REFERENCES.md            # short curated reading list
├── src/learn_langgraph/         # shared core library used by every demo
│   ├── config.py                #   settings loaded from .env
│   ├── llm.py                   #   get_chat_model() / get_embeddings() (Ollama or Anthropic)
│   ├── tools.py                 #   toy tools (weather, add, multiply)
│   └── display.py               #   stream printing + Mermaid graph export
├── demos/                       # numbered, basic → advanced
│   ├── 00_check_setup.py
│   ├── 01_chat_model_basics.py          LangChain: messages, stream, LCEL
│   ├── 02_tools_and_structured_output.py  tool calls by hand, Pydantic output
│   ├── 03_state_graph_basics.py         State, reducers, edges, loops (no LLM)
│   ├── 04_llm_router.py                 workflow: classify → branch
│   ├── 05_tool_agent.py                 ReAct agent as an explicit graph + memory
│   ├── 06_create_agent.py               the same agent, prebuilt
│   ├── 07_human_in_the_loop.py          interrupt() / Command(resume=)
│   ├── 08_rag_agent.py                  embeddings + vector store as a tool
│   ├── 09_map_reduce_send.py            parallel fan-out with Send
│   ├── 10_persistence_time_travel.py    SQLite checkpoints, replay, fork
│   ├── 11_multi_agent_supervisor.py     supervisor delegating to sub-agents (Command)
│   └── output/                          generated .mmd diagrams, sqlite db (git-ignored)
├── tests/                       # pytest smoke tests (each demo runs end to end)
├── .env.example
└── pyproject.toml               # managed with uv, Python 3.14
```

## Setup

```powershell
uv sync                          # create .venv and install dependencies
copy .env.example .env           # adjust if needed

# Local model (Ollama in Docker)
docker start ollama
docker exec ollama ollama pull qwen3:4b-instruct # ~2.5 GB, tool calling, fits a 4 GB GPU
docker exec ollama ollama pull nomic-embed-text  # embeddings for demo 08

uv run demos/00_check_setup.py
```

To use Claude instead, set `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY` in `.env`. Demo 08 still uses Ollama for embeddings.

## Running the demos

```powershell
uv run demos/03_state_graph_basics.py
```

Each demo begins with a docstring explaining the concepts it covers. Demos that build a graph save a Mermaid diagram to `demos/output/*.mmd`; paste one into <https://mermaid.live> to view it.

## Tests

```powershell
uv run pytest -m "not llm"       # fast: tools + LLM-free demos (seconds)
uv run pytest                    # everything; LLM demos are skipped if the backend is unreachable
```

## Notes on the small local model

- `qwen3:4b-instruct` is the non-thinking Qwen3-4B-Instruct-2507 (the plain `qwen3:4b` tag is now the *Thinking* variant, which is slower and prints its reasoning). With `OLLAMA_NUM_CTX=4096` it runs 100% on a 4 GB GPU. Its tool calling is good enough for these demos, but it will sometimes make mistakes that a large model would not. Switching to Anthropic is a useful comparison.
- If VRAM is tight, set `OLLAMA_MODEL=qwen3:1.7b` or lower `OLLAMA_NUM_CTX`.
- Removing models you no longer need frees disk space:
  ```powershell
  docker exec ollama ollama list                 # what is installed (and sizes)
  docker exec ollama ollama rm qwen3:4b          # thinking variant, not used by the demos
  docker exec ollama ollama rm qwen3:8b qwen3:8b-32k gemma4:e2b gemma4:e2b-32k   # too big for 4 GB VRAM
  ```
- Optional tracing: set `LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY=...` to inspect every step in LangSmith.
