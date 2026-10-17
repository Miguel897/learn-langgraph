"""03 - StateGraph fundamentals, with NO LLM (pure Python, instant).

Concepts:
  * State: a TypedDict shared by all nodes.
  * Node: a function  state -> partial update (dict).
  * Reducer: Annotated[list, operator.add] means "append" instead of "overwrite".
  * Edges: fixed (add_edge) and conditional (add_conditional_edges).
  * compile() -> a Runnable with invoke / stream.
  * Loops are just edges pointing backwards.
"""
import operator
from typing import Annotated, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from learn_langgraph import header, save_mermaid


class State(TypedDict):
    number: int  # no reducer -> last write wins
    history: Annotated[list[str], operator.add]  # reducer -> updates are appended


def start(state: State) -> dict:
    return {"history": [f"start with {state['number']}"]}


def halve(state: State) -> dict:
    n = state["number"] // 2
    return {"number": n, "history": [f"halve -> {n}"]}


def triple_plus_one(state: State) -> dict:
    n = state["number"] * 3 + 1
    return {"number": n, "history": [f"3n+1 -> {n}"]}


def route(state: State) -> Literal["halve", "triple_plus_one", "__end__"]:
    """Conditional edge: returns the NAME of the next node (or END)."""
    n = state["number"]
    if n == 1:
        return END
    return "halve" if n % 2 == 0 else "triple_plus_one"


builder = StateGraph(State)
builder.add_node("start", start)
builder.add_node("halve", halve)
builder.add_node("triple_plus_one", triple_plus_one)

builder.add_edge(START, "start")
for node in ("start", "halve", "triple_plus_one"):
    builder.add_conditional_edges(node, route)  # Literal type hint draws the edges

graph = builder.compile()
save_mermaid(graph, "03_collatz")

header("invoke(): run to the end, get the final state")
final = graph.invoke({"number": 6, "history": []})
print("\n".join(final["history"]))

header('stream(stream_mode="updates"): see each node\'s update as it happens')
for update in graph.stream({"number": 3, "history": []}, stream_mode="updates"):
    print(update)
