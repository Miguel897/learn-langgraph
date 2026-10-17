"""04 - Workflow pattern: an LLM router.

A *workflow* has a fixed set of paths chosen by code; an *agent* lets the model
choose its own next step (demo 05). Here the LLM only classifies, and a
conditional edge sends the request to a specialised node.

    START -> classify --(billing)--> billing_agent  -> END
                      \\-(tech)----> tech_agent     -> END
                      \\-(other)---> general_agent  -> END
"""
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from learn_langgraph import get_chat_model, header, save_mermaid

model = get_chat_model()


class Route(BaseModel):
    category: Literal["billing", "tech", "other"] = Field(
        description="billing = payments/invoices, tech = bugs/errors/how-to, other = anything else"
    )


class State(TypedDict, total=False):
    question: str
    category: str
    answer: str


def classify(state: State) -> dict:
    route = model.with_structured_output(Route).invoke(
        [("system", "Classify the customer message. Use 'billing' ONLY for payments, charges, "
                    "refunds or invoices; 'tech' for bugs, errors or how-to; 'other' for "
                    "everything else (locations, opening hours, company info...)."),
         ("human", state["question"])]
    )
    return {"category": route.category}


def make_specialist(persona: str):
    def node(state: State) -> dict:
        reply = model.invoke(
            [("system", f"You are a {persona}. Answer in 2 sentences max."),
             ("human", state["question"])]
        )
        return {"answer": reply.content}
    return node


builder = StateGraph(State)
builder.add_node("classify", classify)
builder.add_node("billing_agent", make_specialist("friendly billing specialist"))
builder.add_node("tech_agent", make_specialist("senior support engineer"))
builder.add_node("general_agent", make_specialist("helpful receptionist"))

builder.add_edge(START, "classify")
builder.add_conditional_edges(
    "classify",
    lambda s: s["category"],
    # path_map: router output -> node name (also used to draw the diagram)
    {"billing": "billing_agent", "tech": "tech_agent", "other": "general_agent"},
)
for n in ("billing_agent", "tech_agent", "general_agent"):
    builder.add_edge(n, END)

graph = builder.compile()
save_mermaid(graph, "04_router")

for q in [
    "I was charged twice for my subscription this month.",
    "The app crashes with error 500 when I upload a file.",
    "Do you have an office in Madrid?",
]:
    header(q)
    out = graph.invoke({"question": q})
    print(f"[{out['category']}] {out['answer']}")
