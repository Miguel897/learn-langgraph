# Curated references

A short, opinionated path. Read top to bottom; each item maps to demos in `demos/`.

## 1. Mental model first
| # | Resource | Why read it | Demos |
|---|----------|-------------|-------|
| 1 | [Building effective agents (Anthropic)](https://www.anthropic.com/engineering/building-effective-agents) | Best short essay on *workflows vs agents* and the common patterns (routing, parallelisation, orchestrator-workers…). Framework-agnostic. | 04, 05, 09 |
| 2 | [ReAct paper (Yao et al., 2022)](https://arxiv.org/abs/2210.03629) | The "reason → act → observe" loop every tool agent implements. Skim the intro and figures. | 05 |
| 3 | [Thinking in LangGraph](https://docs.langchain.com/oss/python/langgraph/thinking-in-langgraph) | How to decompose a problem into state, nodes and edges. | 03 |

## 2. Official docs (LangChain / LangGraph v1)
| # | Resource | Why read it | Demos |
|---|----------|-------------|-------|
| 4 | [LangChain overview](https://docs.langchain.com/oss/python/langchain/overview) | Models, messages, tools, structured output. | 01, 02 |
| 5 | [LangChain agents (`create_agent`)](https://docs.langchain.com/oss/python/langchain/agents) | The prebuilt agent loop, middleware and `response_format`. | 06 |
| 6 | [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview) | Entry point: what LangGraph adds (durability, streaming, HITL). | all |
| 7 | [Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api) | **The core reference**: State, reducers, nodes, edges, `Send`, `Command`. | 03, 09 |
| 8 | [Workflows and agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents) | Each pattern from (1) implemented in LangGraph. | 04, 09 |
| 9 | [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence) & [Time travel](https://docs.langchain.com/oss/python/langgraph/use-time-travel) | Checkpointers, threads, state history, forking. | 05, 10 |
| 10 | [Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) | `interrupt()` / `Command(resume=…)` for human-in-the-loop. | 07 |
| 11 | [RAG tutorial](https://docs.langchain.com/oss/python/langchain/rag) | Embeddings, vector stores, retrieval as a tool. | 08 |
| 12 | [Multi-agent](https://docs.langchain.com/oss/python/langchain/multi-agent) | Supervisor / handoff architectures — the natural next step. | 11 |

## 3. Hands-on course
- [LangChain Academy — Introduction to LangGraph](https://academy.langchain.com/courses/intro-to-langgraph) (free, video + notebooks). Best structured course; modules 1–4 cover everything in this repo.

## 4. Tooling
- [LangGraph GitHub](https://github.com/langchain-ai/langgraph) — source and `examples/`. Reading `langgraph/graph/state.py` is surprisingly instructive.
- [LangSmith](https://docs.langchain.com/langsmith/home) — tracing/evals. Set `LANGSMITH_TRACING=true` + `LANGSMITH_API_KEY` to see every node/LLM call (free tier).
- [LangGraph local server / Studio](https://docs.langchain.com/oss/python/langgraph/local-server) — visual debugger for your graphs.
- [ChatOllama integration](https://docs.langchain.com/oss/python/integrations/chat/ollama) and [Ollama Qwen3 models](https://ollama.com/library/qwen3) — local models used here.

## 5. Beyond the basics (demos 13–15, `deploy/`)
| Resource | Why read it | Where |
|----------|-------------|-------|
| [LangSmith evaluation](https://docs.langchain.com/langsmith/evaluation) | Datasets, evaluators, experiments; the hosted version of demo 13. | 13 |
| [Langfuse LangChain integration](https://langfuse.com/docs/integrations/langchain/tracing) | CallbackHandler, traces and scores; self-host or cloud. | 13, `tracing.py` |
| [Model Context Protocol](https://modelcontextprotocol.io) | The spec and SDKs behind demos 14 and 15. | 14, 15 |
| [langchain-mcp-adapters](https://github.com/langchain-ai/langchain-mcp-adapters) | `MultiServerMCPClient`: MCP tools as LangChain tools. | 14, 15 |
| [n8n MCP Server Trigger](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-langchain.mcptrigger/) | Exposing n8n workflows as MCP tools. | 15 |
| [n8n Docker / queue mode](https://docs.n8n.io/hosting/) | Self-hosting n8n properly (Postgres, Redis workers). | `deploy/` |
| [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence) | Postgres checkpointer used by the API. | `deploy/api` |
| [LangGraph deployment options](https://docs.langchain.com/oss/python/langgraph/deploy) | Agent Server / LangSmith Deployment, the "buy" alternative to `app.py`. | `deploy/` |

See also [NOTES.md](NOTES.md) for what was learned building these.

> Tip: the docs site publishes [`llms.txt`](https://docs.langchain.com/llms.txt), an index you can point Claude Code at so its answers are grounded in the current docs.
