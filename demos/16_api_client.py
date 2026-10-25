"""16 - Talking to the deployed agent: an HTTP client for deploy/api/app.py.

    16_api_client.py                     Docker stack (deploy/compose.yaml)
    +-------------------+   HTTP/JSON   +-------------------+      +----------+
    | httpx.Client      |-------------->| FastAPI  :8000    |----->| Postgres |
    |  POST /chat       |               |  create_agent     |      | threads  |
    |  POST /chat/stream|<--- SSE ------|  + checkpointer   |      +----------+
    |  GET /threads/{id}|               +-------------------+
    +-------------------+

Concepts:
  * The client owns the thread_id: reuse it for follow-ups, mint a new one for
    a new conversation. The server keeps the history (in Postgres), so the
    client sends only the new message each turn.
  * Server-Sent Events: read the response line by line as it arrives and
    print tokens immediately (lower perceived latency than waiting for /chat).
  * Plain HTTP: nothing here imports LangGraph; any language can be the client.
  * Needs the stack running: docker compose -f deploy/compose.yaml up -d --build
"""
import json
import os
import uuid

import httpx

from learn_langgraph import header

API_URL = os.getenv("AGENT_API_URL", "http://localhost:8000")


def chat(client: httpx.Client, thread_id: str, message: str) -> dict:
    response = client.post("/chat", json={"thread_id": thread_id, "message": message})
    response.raise_for_status()
    return response.json()


def chat_stream(client: httpx.Client, thread_id: str, message: str) -> str:
    """Print tokens as they arrive; return the full answer."""
    tokens = []
    payload = {"thread_id": thread_id, "message": message}
    with client.stream("POST", "/chat/stream", json=payload) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line.startswith("data: "):
                continue  # SSE separates events with blank lines
            data = line.removeprefix("data: ")
            if data == "[DONE]":
                break
            tokens.append(json.loads(data))
            print(tokens[-1], end="", flush=True)
    print()
    return "".join(tokens)


if __name__ == "__main__":
    with httpx.Client(base_url=API_URL, timeout=300) as client:  # small local models can be slow
        header(f"Health: {API_URL}")
        print(client.get("/health").json())

        thread_id = f"demo16-{uuid.uuid4().hex[:8]}"
        header(f"Two turns on thread {thread_id} (memory lives on the server)")
        for message in ["What's the weather in London?", "Add 10 to the temperature there."]:
            reply = chat(client, thread_id, message)
            print(f"User: {message}\nAgent: {reply['answer']}   [tools: {reply['tools']}]\n")

        header("Same thread, streamed token by token")
        chat_stream(client, thread_id, "In one sentence, summarise what we discussed.")

        header("Stored conversation (GET /threads/{id})")
        for m in client.get(f"/threads/{thread_id}").json():
            if m["content"]:  # skip empty AI messages that only carried tool calls
                print(f"  {m['role']:>5}: {m['content']}")

        header("Unknown thread -> 404")
        print(client.get("/threads/does-not-exist").status_code)
