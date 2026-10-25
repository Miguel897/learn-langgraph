"""A LangGraph agent served over HTTP: FastAPI + Postgres checkpointer.

    client --HTTP--> FastAPI  --ainvoke/astream-->  agent (create_agent)
                       |                               |
                       |                        AsyncPostgresSaver
                       |                               v
                       +--- GET /threads/{id} --->  Postgres (one row set per thread)

Concepts:
  * Lifespan: open the connection pool and build the graph once per process,
    not per request. checkpointer.setup() creates the tables (idempotent).
  * thread_id comes from the client: any replica can serve any turn because
    the conversation lives in Postgres, not in memory (stateless API).
  * /chat returns the final answer; /chat/stream sends tokens as Server-Sent
    Events using stream_mode="messages".
  * Run it with Docker (see README "Deploy"). psycopg's async driver does not
    work on Windows' default event loop, which is another reason to containerise.
Try: http://localhost:8000/docs
"""
import json
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from langchain.agents import create_agent
from langchain_core.messages import AIMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from pydantic import BaseModel

from learn_langgraph import BASIC_TOOLS, get_chat_model

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://langgraph:langgraph@localhost:5433/langgraph")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Settings required by the Postgres checkpointer (autocommit, no prepared statements).
    pool_kwargs = {"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row}
    async with AsyncConnectionPool(DATABASE_URL, kwargs=pool_kwargs, open=False) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()
        app.state.agent = create_agent(
            model=get_chat_model(),
            tools=BASIC_TOOLS,
            system_prompt="Always use tools for weather and maths. Answer in one short sentence.",
            checkpointer=checkpointer,
        )
        yield


app = FastAPI(title="learn-langgraph agent API", lifespan=lifespan)


class ChatIn(BaseModel):
    thread_id: str
    message: str


class ChatOut(BaseModel):
    thread_id: str
    answer: str
    tools: list[str]


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/chat")
async def chat(body: ChatIn, request: Request) -> ChatOut:
    agent = request.app.state.agent
    before = (await agent.aget_state(_config(body.thread_id))).values.get("messages", [])
    result = await agent.ainvoke({"messages": [("user", body.message)]}, _config(body.thread_id))
    new = result["messages"][len(before):]  # only this turn's messages
    tools = [c["name"] for m in new if isinstance(m, AIMessage) for c in m.tool_calls]
    return ChatOut(thread_id=body.thread_id, answer=result["messages"][-1].text, tools=tools)


@app.post("/chat/stream")
async def chat_stream(body: ChatIn, request: Request) -> StreamingResponse:
    agent = request.app.state.agent

    async def events():
        async for chunk, meta in agent.astream(
            {"messages": [("user", body.message)]}, _config(body.thread_id), stream_mode="messages"
        ):
            if meta["langgraph_node"] == "model" and chunk.text:  # skip tool outputs
                yield f"data: {json.dumps(chunk.text)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@app.get("/threads/{thread_id}")
async def thread_history(thread_id: str, request: Request) -> list[dict]:
    state = await request.app.state.agent.aget_state(_config(thread_id))
    if not state.values:
        raise HTTPException(404, f"No thread {thread_id!r}")
    return [{"role": m.type, "content": m.text} for m in state.values["messages"]]
