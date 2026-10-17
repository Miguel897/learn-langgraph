"""06 - The same agent in one call: langchain.agents.create_agent.

create_agent builds the demo-05 loop for you (it returns a compiled LangGraph
graph), plus extras: a system prompt, middleware hooks, structured responses.
Use it for the standard loop; write your own StateGraph when you need custom
nodes, branching or bespoke state.
"""
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel

from learn_langgraph import BASIC_TOOLS, get_chat_model, header, print_messages_stream, save_mermaid

agent = create_agent(
    model=get_chat_model(),
    tools=BASIC_TOOLS,
    system_prompt="You are a weather assistant. Always use tools for weather and maths.",
    checkpointer=InMemorySaver(),
)
save_mermaid(agent, "06_create_agent")

config = {"configurable": {"thread_id": "t1"}}
header("Multi-step: two tool calls in one turn")
print_messages_stream(
    agent,
    {"messages": [("user", "What's the sum of the temperatures in Madrid and London?")]},
    config,
)


header("response_format: get a typed object back as well")


class WeatherReport(BaseModel):
    city: str
    temperature_c: float
    summary: str


typed_agent = create_agent(
    model=get_chat_model(),
    tools=BASIC_TOOLS,
    system_prompt="Never guess weather: call get_weather first, then fill the report from its result.",
    response_format=WeatherReport,
)
result = typed_agent.invoke({"messages": [("user", "Report the weather in Tokyo.")]})
print("tools called:", [c["name"] for m in result["messages"] for c in getattr(m, "tool_calls", [])])
print(repr(result["structured_response"]))
