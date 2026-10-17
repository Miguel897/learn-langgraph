"""12 - Subgraphs and stream modes.

    parent:    START -> prepare -> research (subgraph) -> write -> END
    subgraph:  START -> search -> summarize -> END

Concepts:
  * A compiled graph is a Runnable, so it can be added as a node of another
    graph. Keys shared by both states (here `topic` and `notes`) flow in and
    out automatically; subgraph-only keys (`hits`) stay private.
  * stream(subgraphs=True) also yields events from inside subgraphs, tagged
    with a namespace tuple such as ('research:<task id>',).
  * stream_mode picks WHAT you see:
      "values"   full state after each step         (used in earlier demos)
      "updates"  only what each node returned
      "custom"   anything a node sends with get_stream_writer()
      "messages" LLM tokens as they are generated, plus metadata
    Pass a list of modes to get (mode, chunk) pairs.
"""
import operator
from typing import Annotated, TypedDict

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from learn_langgraph import get_chat_model, header, save_mermaid

model = get_chat_model()

_FAKE_INDEX = {
    "langgraph": ["graphs of nodes and edges", "checkpointers for memory", "interrupt() for humans"],
}


# --- Subgraph: its own state, sharing `topic` and `notes` with the parent ----
class ResearchState(TypedDict, total=False):
    topic: str
    hits: list[str]                          # private to the subgraph
    notes: Annotated[list[str], operator.add]


def search(state: ResearchState) -> dict:
    writer = get_stream_writer()
    hits = _FAKE_INDEX.get(state["topic"].lower(), [])
    for i, hit in enumerate(hits, 1):
        writer({"progress": f"found {i}/{len(hits)}: {hit}"})  # -> stream_mode="custom"
    return {"hits": hits}


def summarize(state: ResearchState) -> dict:
    return {"notes": [f"{len(state['hits'])} facts about {state['topic']}"] + state["hits"]}


research_builder = StateGraph(ResearchState)
research_builder.add_node("search", search)
research_builder.add_node("summarize", summarize)
research_builder.add_edge(START, "search")
research_builder.add_edge("search", "summarize")
research_builder.add_edge("summarize", END)
research = research_builder.compile()


# --- Parent graph -------------------------------------------------------------
class State(TypedDict, total=False):
    topic: str
    notes: Annotated[list[str], operator.add]
    summary: str


def prepare(state: State) -> dict:
    return {"notes": [f"request: explain {state['topic']}"]}


def write(state: State) -> dict:
    reply = model.invoke(
        "Using only these notes, write one short sentence for a beginner:\n- " + "\n- ".join(state["notes"])
    )
    return {"summary": reply.content}


builder = StateGraph(State)
builder.add_node("prepare", prepare)
builder.add_node("research", research)  # a compiled graph used as a node
builder.add_node("write", write)
builder.add_edge(START, "prepare")
builder.add_edge("prepare", "research")
builder.add_edge("research", "write")
builder.add_edge("write", END)

graph = builder.compile()
save_mermaid(graph, "12_subgraphs")
inputs = {"topic": "LangGraph"}

header('stream_mode="updates": the subgraph looks like one node')
for update in graph.stream(inputs, stream_mode="updates"):
    print("->", list(update))

header('stream_mode="updates", subgraphs=True: see inside, with a namespace')
for namespace, update in graph.stream(inputs, stream_mode="updates", subgraphs=True):
    print(f"{namespace or '(parent)'} -> {list(update)}")

header('stream_mode=["custom", "updates"]: progress events from get_stream_writer()')
# With a list of modes AND subgraphs=True, each item is (namespace, mode, chunk).
for namespace, mode, chunk in graph.stream(inputs, stream_mode=["custom", "updates"], subgraphs=True):
    if mode == "custom":
        print("  custom:", chunk["progress"])
    else:
        print(f"  update: {namespace or '(parent)'} -> {list(chunk)}")

header('stream_mode="messages": LLM tokens as they arrive')
for token, metadata in graph.stream(inputs, stream_mode="messages"):
    if metadata["langgraph_node"] == "write" and token.content:
        print(token.content, end="", flush=True)
print()
