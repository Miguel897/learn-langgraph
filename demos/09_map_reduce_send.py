"""09 - Map-reduce / fan-out with the Send API.

The number of parallel branches is only known at runtime:

    START -> plan --Send x N--> write_section (in parallel) --> combine -> END

Concepts:
  * Returning [Send(node, private_state), ...] from a conditional edge spawns
    one task per item, each with its OWN input (not the shared state).
  * Parallel results are merged into shared state by a reducer (operator.add).
  * Steps run in "super-steps": combine waits until every branch finished.
"""
import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from pydantic import BaseModel

from learn_langgraph import get_chat_model, header, save_mermaid

model = get_chat_model(temperature=0.5)


class OverallState(TypedDict, total=False):
    topic: str
    sections: list[str]
    drafts: Annotated[list[str], operator.add]  # parallel writes get concatenated
    article: str


class SectionState(TypedDict):
    topic: str
    section: str


class Plan(BaseModel):
    sections: list[str]


def plan(state: OverallState) -> dict:
    p = model.with_structured_output(Plan).invoke(
        f"List exactly 3 short section titles for a mini-article about: {state['topic']}"
    )
    return {"sections": p.sections[:3]}


def fan_out(state: OverallState) -> list[Send]:
    return [Send("write_section", {"topic": state["topic"], "section": s}) for s in state["sections"]]


def write_section(state: SectionState) -> dict:
    text = model.invoke(
        f"Write 2 sentences for the section '{state['section']}' of an article on {state['topic']}."
    ).content
    return {"drafts": [f"## {state['section']}\n{text}"]}


def combine(state: OverallState) -> dict:
    return {"article": f"# {state['topic']}\n\n" + "\n\n".join(state["drafts"])}


builder = StateGraph(OverallState)
builder.add_node("plan", plan)
builder.add_node("write_section", write_section)
builder.add_node("combine", combine)
builder.add_edge(START, "plan")
builder.add_conditional_edges("plan", fan_out, ["write_section"])
builder.add_edge("write_section", "combine")
builder.add_edge("combine", END)

graph = builder.compile()
save_mermaid(graph, "09_map_reduce")

header("Streaming node updates (watch the parallel branches)")
for update in graph.stream({"topic": "Why octopuses are smart"}, stream_mode="updates"):
    print("->", list(update))

header("Final article")
print(graph.invoke({"topic": "Why octopuses are smart"})["article"])
