# Technical notes

Things learned while building demos 13–15 and the `deploy/` stack (October 2026). For how to run the stack, see [deploy/README.md](../deploy/README.md).

## 1. Evaluating agents (demo 13)

- Score the **trajectory** (which tools were called) as well as the answer. In practice `qwen3:4b-instruct` often adds 14 + 22 "in its head" instead of calling `add`: the answer is right, the LLM judge passes it, and only the trajectory check fails. That is exactly the bug a judge-only eval misses.
- Order evaluators from cheap and exact (set comparison, substring) to fuzzy (LLM-as-judge). Judges are noisy, and small judges ramble; keep the rubric binary and truncate the reasoning in output.
- A pass-rate **gate** (`MIN_PASS_RATE = 0.75`, non-zero exit) turns the demo into a CI regression check. With a small model, gate the aggregate, not each case, or it is flaky.
- Hosted options: LangSmith `Client.evaluate()` (needs `LANGSMITH_API_KEY`, free tier) or Langfuse datasets. Writing evaluators as `(inputs, outputs, reference_outputs)` functions keeps them portable to LangSmith.

## 2. Tracing with Langfuse

- `learn_langgraph.tracing_config(trace_id)` returns `{"callbacks": [CallbackHandler]}` when `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` are set, and `{}` otherwise, so demos and tests run unchanged without keys.
- Langfuse SDK v5: there is no `handler.last_trace_id`. Create the id first (`get_client().create_trace_id()`), pass it via `CallbackHandler(trace_context={"trace_id": ...})`, then attach scores with `create_score(trace_id=..., data_type="BOOLEAN")`. Call `flush()` before the process exits.
- Self-hosted Langfuse v3 is ~6 containers (Postgres, ClickHouse, Redis, MinIO, web, worker), roughly 4 GB RAM; Langfuse Cloud's free tier only needs two keys. **Not yet verified against a live server.**
- LangSmith tracing needs no code at all (`LANGSMITH_TRACING=true` + key); it hooks into LangChain callbacks automatically.

## 3. MCP (demos 14 and 15)

| | Demo 14 (stdio) | Demo 15 (streamable HTTP) |
|---|---|---|
| Server | `demos/mcp_server.py` (FastMCP), started as a child process | n8n workflow with an MCP Server Trigger node |
| Client config | `{"transport": "stdio", "command": sys.executable, "args": [...]}` | `{"transport": "streamable_http", "url": "http://localhost:5678/mcp/toolbox"}` |
| Lifecycle | lives and dies with the client | long-running service, shared by many clients |

- `langchain-mcp-adapters` (`MultiServerMCPClient.get_tools()`) turns MCP tools into LangChain tools; local and MCP tools mix in one `create_agent`.
- MCP tools are **async only**: use `ainvoke` / `astream` inside `asyncio.run`.
- Results arrive as MCP content blocks (`[{"type": "text", "text": "..."}]`), not bare values. Models handle this fine.
- A stdio server must never `print()`: stdout carries the protocol.
- Use `sys.executable` as the command so the server runs in the same venv.

## 4. n8n as a tool provider

- The **MCP Server Trigger** node exposes every tool node wired to it (Code Tool, HTTP Request Tool, Gmail, Postgres, …) as an MCP server. Code Tools without an input schema take one string argument named `input` (available as `query` in the JS code).
- The production URL `/mcp/<path>` only works when the workflow is **published** (n8n 2.x replaced "active" with draft/publish). In the editor, `/mcp-test/<path>` works while you are testing.
- Workflows can be deployed without the UI: `n8n import:workflow --input=file.json` then `n8n publish:workflow --id=<id>` (set a fixed 16-character `id` in the JSON), then **restart** n8n. `update:workflow --active` is deprecated in 2.x.
- Node type ids/versions in 2.44.6: `@n8n/n8n-nodes-langchain.mcpTrigger` (v2.1), `@n8n/n8n-nodes-langchain.toolCode` (v1.3). They can be checked inside the container under `node_modules/@n8n/n8n-nodes-langchain/dist/nodes/`.

## 5. LangGraph vs n8n (summary)

| | LangGraph ecosystem | n8n |
|---|---|---|
| Best at | Custom agent logic: state, loops, interrupts, multi-agent, evals in code | Connecting SaaS apps: 400+ nodes, OAuth credentials, triggers, retries |
| Control | Full (it is your Python) | AI Agent node is configurable, not rewritable |
| Batteries | Few: you build API, auth, queue (or buy Agent Server) | Many: editor, execution log, scheduling, users |
| Testing | pytest + eval datasets, plain git | Harder; workflows are JSON |
| Deploy | Your container + Postgres, or LangSmith Deployment | `docker run n8nio/n8n`; queue mode with Redis for scale |
| Licence | MIT | Sustainable Use License (fair-code) |

The hybrid used in demo 15 is common: **n8n owns integrations, LangGraph owns reasoning**, joined by MCP (or by n8n calling the agent API over HTTP). Swapping n8n's Code tools for real app nodes needs no agent code changes.

Job-market signal (one vendor job board, spring 2026, indicative only): LangGraph ranked second after LangChain in agentic-AI job ads; ads typically name ~2 frameworks. Fundamentals (tool calling, evals, observability, MCP) matter as much as the framework.

## 6. Serving an agent over HTTP (`deploy/api/app.py`)

- Build the graph **once** in the FastAPI lifespan; open an `AsyncConnectionPool` with `autocommit=True, prepare_threshold=0, row_factory=dict_row` (required by `AsyncPostgresSaver`); `await checkpointer.setup()` is idempotent.
- The client sends `thread_id`; state lives in Postgres, so the API is stateless and any replica can serve any turn (verified by restarting the container mid-conversation).
- To return only the current turn, read the message count with `aget_state()` before invoking and slice afterwards.
- Token streaming: `astream(..., stream_mode="messages")` yields `(chunk, metadata)`; keep chunks where `metadata["langgraph_node"] == "model"` to skip tool output; send as SSE.
- psycopg async does not run on Windows' default Proactor event loop: run the API in Docker or WSL.

## 7. Environment gotchas (Windows + Docker)

- Git Bash rewrites absolute container paths (`/import/x` → `C:/Program Files/Git/import/x`) in `docker exec` arguments: use PowerShell or `MSYS_NO_PATHCONV=1`.
- Windows console code page garbles `°`: set `PYTHONIOENCODING=utf-8`.
- Containers reach host services (the Ollama container's published port) through `host.docker.internal`.
- Postgres 18 moved the data directory: mount the volume at `/var/lib/postgresql`, not `/var/lib/postgresql/data`. Postgres 19 was only at RC1 on 2026-10-25.
- Pin images to versions: n8n `2.44.6` matched the `stable` tag's digest at the time; `v3-nightly` tags also exist.
