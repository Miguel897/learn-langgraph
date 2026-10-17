"""05 - A tool-calling agent as an explicit LangGraph graph (the ReAct loop).

    START -> agent --(tool calls?)--> tools --+
               ^                              |
               +------------------------------+
             (no tool calls) -> END

Concepts:
  * MessagesState: shared state with a `messages` list using the add_messages
    reducer, so each node's returned messages are APPENDED to the history.
  * ToolNode: prebuilt node that executes the tool calls in the last AIMessage.
  * tools_condition: prebuilt router -> "tools" if there are tool calls, else END.
  * Checkpointer + thread_id: conversation memory across invocations, which is
    why the second question can say "there".
"""
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from learn_langgraph import BASIC_TOOLS, get_chat_model, header, print_messages_stream, save_mermaid

llm = get_chat_model().bind_tools(BASIC_TOOLS)


def agent(state: MessagesState) -> dict:
    response = llm.invoke(state["messages"])
    return {"messages": [response]}  # appended, not overwritten


builder = StateGraph(MessagesState)
builder.add_node("agent", agent)
builder.add_node("tools", ToolNode(BASIC_TOOLS))

builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", tools_condition)
builder.add_edge("tools", "agent")  # feed tool results back to the model

graph = builder.compile(checkpointer=InMemorySaver())
save_mermaid(graph, "05_tool_agent")

if __name__ == "__main__":
    config = {"configurable": {"thread_id": "demo-1"}}
    for question in [
        "What's the weather in Madrid?",
        "Multiply the temperature there by 3.",  # relies on memory from turn 1
    ]:
        header(f"User: {question}")
        print_messages_stream(graph, {"messages": [("user", question)]}, config)
