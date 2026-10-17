"""07 - Human in the loop with interrupt() and Command(resume=...).

A "dangerous" tool asks for human approval before it runs:

  * interrupt(payload) pauses the graph and surfaces `payload` to the caller.
    The state is saved by the checkpointer (required!).
  * The caller inspects the pause, then calls graph.invoke(Command(resume=value)).
  * The node re-runs from its start and interrupt() now returns `value`.
"""
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import Command, interrupt

from learn_langgraph import get_chat_model, header, print_messages_stream


@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email."""
    decision = interrupt({"action": "send_email", "to": to, "subject": subject, "body": body})
    if decision.get("approved"):
        return f"Email sent to {to}."
    return f"User rejected sending the email. Reason: {decision.get('reason', 'n/a')}"


tools = [send_email]
llm = get_chat_model().bind_tools(tools)

builder = StateGraph(MessagesState)
builder.add_node("agent", lambda s: {"messages": [llm.invoke(s["messages"])]})
builder.add_node("tools", ToolNode(tools))
builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", tools_condition)
builder.add_edge("tools", "agent")
graph = builder.compile(checkpointer=InMemorySaver())  # interrupts need a checkpointer

config = {"configurable": {"thread_id": "hitl-1"}}

header("Run until the interrupt")
print_messages_stream(
    graph,
    {"messages": [("user", "Email bob@example.com with subject 'Lunch' saying I'll be 10 minutes late.")]},
    config,
)

snapshot = graph.get_state(config)
print("\nPaused before node(s):", snapshot.next)
for task in snapshot.tasks:
    for intr in task.interrupts:
        print("Approval requested:", intr.value)

answer = input("\nApprove? [y/N] ").strip().lower()
resume = {"approved": True} if answer == "y" else {"approved": False, "reason": "not now"}

header("Resume with Command(resume=...)")
print_messages_stream(graph, Command(resume=resume), config)
