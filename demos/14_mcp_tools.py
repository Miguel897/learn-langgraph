"""14 - Tools from an MCP server, used by a LangGraph agent.

    14_mcp_tools.py                          mcp_server.py (child process)
    +--------------------------+   stdio    +---------------------------+
    | MultiServerMCPClient     |<---------->| FastMCP "toolbox"         |
    |   get_tools() -> tools --+--+         |   celsius_to_fahrenheit   |
    +--------------------------+  |         |   word_count              |
                                  v         +---------------------------+
             create_agent(tools = BASIC_TOOLS + MCP tools)

Concepts:
  * MCP (Model Context Protocol): an open standard for exposing tools,
    resources and prompts to any AI app. Write a server once; Claude Code,
    Claude Desktop or this agent can all use it.
  * langchain-mcp-adapters: MultiServerMCPClient starts/connects to servers
    (stdio or streamable HTTP) and converts their tools into LangChain tools.
  * Local and MCP tools mix freely in one agent.
  * MCP tools are async: run the agent with ainvoke/astream inside asyncio.
"""
import asyncio
import sys
from pathlib import Path

from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient

from learn_langgraph import BASIC_TOOLS, get_chat_model, header, save_mermaid

SERVER = Path(__file__).with_name("mcp_server.py")

client = MultiServerMCPClient(
    {
        "toolbox": {
            "transport": "stdio",
            "command": sys.executable,  # same venv, so the server can import `mcp`
            "args": [str(SERVER)],
        }
    }
)


async def main() -> None:
    header("Tools discovered from the MCP server")
    mcp_tools = await client.get_tools()
    for t in mcp_tools:
        print(f"  {t.name}: {t.description}")

    header("Calling an MCP tool directly")
    # Results come back as MCP content blocks, not bare Python values.
    word_count = next(t for t in mcp_tools if t.name == "word_count")
    print("  word_count ->", await word_count.ainvoke({"text": "hello MCP world"}))

    agent = create_agent(
        model=get_chat_model(),
        tools=BASIC_TOOLS + mcp_tools,
        system_prompt="Always use tools for weather, maths and conversions.",
    )
    save_mermaid(agent, "14_mcp_tools")

    header("Agent mixing a local tool (get_weather) and an MCP tool")
    question = "What's the temperature in Madrid in Fahrenheit?"
    result = await agent.ainvoke({"messages": [("user", question)]})
    for msg in result["messages"]:
        msg.pretty_print()


if __name__ == "__main__":
    asyncio.run(main())
