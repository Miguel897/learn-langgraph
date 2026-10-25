# Deploy: agent API + Postgres + n8n

A local, production-*like* stack. It shows the moving parts of a real deployment; it is not hardened (see [Getting closer to production](#getting-closer-to-production)).

```
                  host (Windows)                          Docker: project "learn-langgraph"
  +-----------------------------------+      +--------------------------------------------------+
  | browser / curl / demos/15_*.py    |      |  api       FastAPI + create_agent  :8000         |
  |                                   |----->|    |  AsyncPostgresSaver                          |
  |                                   |      |    v                                             |
  |                                   |      |  postgres  18-alpine  :5433 (host) / 5432 (net)  |
  |                                   |----->|  n8n       2.44.6      :5678  /mcp/toolbox        |
  +-----------------------------------+      +--------------------------------------------------+
                  ^                                    | api -> host.docker.internal:11434
                  +---- ollama container :11434 <------+   (existing, started separately)
```

| Path | What it is |
|------|------------|
| `compose.yaml` | The three services. Ports bound to `127.0.0.1` only. Reads `../.env` (optional) for `LLM_PROVIDER`, `ANTHROPIC_API_KEY`, `LANGFUSE_*`. |
| `Dockerfile` | uv-based image (`ghcr.io/astral-sh/uv:python3.14-bookworm-slim`), deps layer cached on `uv.lock`, runs as non-root user. |
| `api/app.py` | FastAPI app: graph built once in the lifespan, conversation state in Postgres. |
| `n8n/toolbox.workflow.json` | n8n workflow: MCP Server Trigger + two Code tools (`get_order_status`, `days_until`). |
| `../.dockerignore` | Keeps `.env`, `.venv`, `.git` out of the image. |

## Run it

Prerequisites: Docker Desktop, the `ollama` container running (`docker start ollama`) with `qwen3:4b-instruct` pulled.

```powershell
docker compose -f deploy/compose.yaml up -d --build
docker compose -f deploy/compose.yaml ps            # api Up, postgres healthy, n8n Up
```

### One-time: load the n8n workflow

```powershell
docker compose -f deploy/compose.yaml exec n8n n8n import:workflow --input=/import/toolbox.workflow.json
docker compose -f deploy/compose.yaml exec n8n n8n publish:workflow --id=lgToolboxMcp0001
docker compose -f deploy/compose.yaml restart n8n  # CLI changes are only picked up on start
```

It is stored in the `n8n_data` volume, so this is needed again only after `down -v`. Open <http://localhost:5678> and create the owner account to see and edit it.

### Use the agent API

Interactive docs: <http://localhost:8000/docs>.

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Liveness. |
| `POST /chat` `{"thread_id", "message"}` | Runs one turn; returns `answer` and the `tools` called in this turn. |
| `POST /chat/stream` | Same, streamed as Server-Sent Events (`data: "token"` … `data: [DONE]`). |
| `GET /threads/{id}` | Full conversation stored for a thread; 404 if unknown. |

```powershell
$h = "Content-Type: application/json"
curl.exe -s localhost:8000/chat -H $h -d '{\"thread_id\":\"t1\",\"message\":\"Weather in Madrid?\"}'
curl.exe -s localhost:8000/chat -H $h -d '{\"thread_id\":\"t1\",\"message\":\"Multiply the temperature there by 3.\"}'
curl.exe -s -N localhost:8000/chat/stream -H $h -d '{\"thread_id\":\"t2\",\"message\":\"Say hi in five words.\"}'
curl.exe -s localhost:8000/threads/t1
```

Persistence check: `docker compose -f deploy/compose.yaml restart api` between the two `t1` turns, and the second turn still knows "there" = Madrid.

Or run the Python client, which exercises every endpoint (override the URL with `AGENT_API_URL`):

```powershell
uv run demos/16_api_client.py
```

### Use the n8n tools from LangGraph

```powershell
uv run demos/15_n8n_mcp_tools.py   # agent chains get_order_status -> days_until
```

Override the endpoint with `N8N_MCP_URL`. `uv run pytest` skips demos 15 and 16 when n8n or the API is not reachable.

### Stop / reset

```powershell
docker compose -f deploy/compose.yaml down        # keep data
docker compose -f deploy/compose.yaml down -v     # also delete Postgres + n8n volumes
docker compose -f deploy/compose.yaml up -d --build api   # rebuild after code changes
```

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| `ENOENT ... C:/Program Files/Git/import/...` | Git Bash rewrites `/import/...`. Run the `exec` commands from PowerShell, or prefix with `MSYS_NO_PATHCONV=1`. |
| `/mcp/toolbox` returns 404 | Workflow not published, or n8n not restarted after `publish:workflow`. Check `docker compose ... logs n8n` for "1 published workflows". |
| `Unknown SSE event: endpoint` log lines | Harmless: n8n sends an extra SSE event the MCP client does not use. Demo 15 silences that logger. |
| API answers slowly / times out | First request loads the model into the GPU; check `docker logs ollama`. The 4 GB GPU serves one request at a time. |
| API cannot reach Ollama | The container uses `http://host.docker.internal:11434`; the `ollama` container must publish port 11434. |
| Running `app.py` with uvicorn directly on Windows fails | psycopg's async driver does not support Windows' default Proactor event loop. Run it in Docker (as here) or under WSL. |
| Postgres container restarts after changing the image | Postgres 18+ stores data under `/var/lib/postgresql/<major>/`; volumes from 17 (`.../data`) are not compatible. `down -v` for a fresh start or use `pg_upgrade`. |

## Getting closer to production

Roughly in priority order. ✅ = already done here.

### Security
- **Authenticate the API** (API key header, or OAuth/JWT behind a gateway) and add rate limiting.
- **Scope threads to users.** Today any caller who knows a `thread_id` can read or continue it. Derive the thread key from the authenticated user (e.g. `f"{user_id}:{thread_id}"`) or store ownership and check it.
- **Secrets**: no default passwords; `DATABASE_URL`, API keys and `N8N_ENCRYPTION_KEY` from a secret manager or Docker secrets. ✅ `.env` is excluded from the image.
- **n8n MCP auth**: set *Bearer Auth* on the MCP Server Trigger node; the endpoint is currently open to anything that can reach port 5678.
- **TLS + reverse proxy** (Caddy, Traefik, nginx) in front of both services; set n8n `N8N_HOST`, `N8N_PROTOCOL=https`, `WEBHOOK_URL`.
- ✅ Ports bound to `127.0.0.1`; ✅ API image runs as a non-root user.

### Reliability
- **Limits per request**: `recursion_limit` in the run config, model timeouts and max tokens, request body size limits.
- **Retries** for transient model/API errors (`model.with_retry(...)` or agent middleware), and map failures to clean HTTP errors (502/504) instead of 500s.
- **Readiness check** that pings Postgres and the model, plus a Docker `healthcheck` for `api` and `n8n`.
- **Long-running runs**: run the agent in a background worker/queue and let clients poll or reconnect to a stream, instead of holding the HTTP request open. Needed for human-in-the-loop (`interrupt()`) too: add a `POST /threads/{id}/resume` that sends `Command(resume=...)`.
- **Checkpoint growth**: every step writes a checkpoint. Add a retention job (delete old threads) and Postgres backups; use managed Postgres in the cloud.

### Scale
- The API is stateless (state is in Postgres), so scale horizontally: more replicas behind a load balancer, or `uvicorn --workers N`. Size the `AsyncConnectionPool` (`min_size`/`max_size`) against Postgres `max_connections`.
- The local 4B model is the bottleneck: use a hosted model (`LLM_PROVIDER=anthropic`) or a GPU server with `OLLAMA_NUM_PARALLEL` / vLLM.
- n8n: **queue mode** (Redis + worker containers) and **Postgres instead of SQLite** for its own database.

### Observability and quality
- Tracing in the API: pass `tracing_config()` (Langfuse) in the run config, or set `LANGSMITH_TRACING=true`. Add structured logs with `thread_id`, latency and token usage.
- Run the eval demo (`demos/13_agent_evals.py`, non-zero exit below the pass-rate gate) in CI against the model and prompt you deploy; grow the dataset from production failures.
- Pin model versions so behaviour does not change under you.

### Delivery
- Build the image in CI, scan it, push to a registry, deploy by immutable tag (Cloud Run, ECS, Kubernetes, or a VPS with Compose).
- Pin base images by digest; upgrade n8n deliberately. `2.44.6` was the `stable` tag on 2026-10-25; `latest` may move to betas and `v3-nightly` exists.
- Keep n8n workflows in git as JSON and promote them with `import:workflow` + `publish:workflow` (as above) rather than editing production by hand. Back up `N8N_ENCRYPTION_KEY`: without it stored credentials cannot be decrypted.
- n8n licence (Sustainable Use License): fine for internal use; not for reselling n8n as a hosted service.

### Buy instead of build
LangGraph's own **Agent Server** (`langgraph.json` + `langgraph build`, or the managed LangSmith Deployment) provides threads, runs, background jobs, cron, streaming, resumable interrupts and Studio out of the box. `app.py` is the do-it-yourself version of a small slice of that; compare them before writing more server code.
