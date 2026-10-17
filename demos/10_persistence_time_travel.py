"""10 - Durable persistence (SQLite) and time travel.

Concepts:
  * SqliteSaver: checkpoints survive process restarts (run this script twice!).
  * A checkpoint is saved after every super-step: graph.get_state_history().
  * Time travel: re-run from any past checkpoint by passing its checkpoint_id.
  * Fork: graph.update_state() writes a modified state as a new branch.
"""
import sqlite3
from pathlib import Path

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import START, MessagesState, StateGraph

from learn_langgraph import get_chat_model, header

DB = Path(__file__).parent / "output" / "checkpoints.sqlite"
DB.parent.mkdir(exist_ok=True)

model = get_chat_model(temperature=0.7)

builder = StateGraph(MessagesState)
builder.add_node("chat", lambda s: {"messages": [model.invoke(s["messages"])]})
builder.add_edge(START, "chat")

with sqlite3.connect(DB, check_same_thread=False) as conn:
    graph = builder.compile(checkpointer=SqliteSaver(conn))
    config = {"configurable": {"thread_id": "poet"}}

    previous = graph.get_state(config).values.get("messages", [])
    header(f"Thread 'poet' already has {len(previous)} messages in {DB.name}")

    graph.invoke({"messages": [HumanMessage("Write a 2-line poem about a cat. Only the poem.")]}, config)
    print(graph.get_state(config).values["messages"][-1].content)

    header("Checkpoint history (newest first)")
    history = list(graph.get_state_history(config))
    for snap in history[:6]:
        last = snap.values["messages"][-1].content[:50] if snap.values.get("messages") else ""
        print(f"step={snap.metadata['step']:>2}  next={snap.next}  last={last!r}")

    header("Time travel: replay from the checkpoint just before the model answered")
    before_chat = next(s for s in history if s.next == ("chat",))
    for update in graph.stream(None, before_chat.config, stream_mode="values"):
        pass
    print("New alternative answer:", update["messages"][-1].content)

    header("Fork: edit the past, then continue from the edited state")
    forked = graph.update_state(
        before_chat.config,
        {"messages": [HumanMessage("Actually, make it about a dog instead.")]},
    )
    result = graph.invoke(None, forked)
    print(result["messages"][-1].content)
