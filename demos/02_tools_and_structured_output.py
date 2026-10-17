"""02 - Tool calling and structured output, done by hand.

Concepts:
  * @tool turns a function into a schema the model can "call".
  * model.bind_tools(tools): the model *requests* calls; YOU execute them.
  * ToolMessage carries the result back, linked by tool_call_id.
  * model.with_structured_output(PydanticModel) returns validated objects.

This manual loop is exactly what LangGraph's ToolNode automates in demo 05.
"""
from langchain_core.messages import HumanMessage, ToolMessage
from pydantic import BaseModel, Field

from learn_langgraph import BASIC_TOOLS, get_chat_model, header

model = get_chat_model()

header("1. The schema the model sees")
print(BASIC_TOOLS[0].name, BASIC_TOOLS[0].args)

header("2. Model decides to call a tool")
llm_with_tools = model.bind_tools(BASIC_TOOLS)
messages = [HumanMessage("What's the weather in Tokyo?")]
ai_msg = llm_with_tools.invoke(messages)
print("tool_calls:", ai_msg.tool_calls)

header("3. We run the tool and send the result back")
messages.append(ai_msg)
tools_by_name = {t.name: t for t in BASIC_TOOLS}
for call in ai_msg.tool_calls:
    result = tools_by_name[call["name"]].invoke(call["args"])
    messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))
final = llm_with_tools.invoke(messages)
print("final answer:", final.content)


header("4. Structured output with Pydantic")


class Movie(BaseModel):
    """Information about a movie."""

    title: str
    year: int = Field(description="Release year")
    genres: list[str]


extractor = model.with_structured_output(Movie)
movie = extractor.invoke("The Matrix came out in 1999; it's sci-fi action.")
print(repr(movie))
