"""15 - An agent using an n8n workflow as its toolbox, over MCP.

    15_n8n_mcp_tools.py                      n8n (Docker, port 5678)
    +--------------------------+  HTTP/MCP  +-------------------------------+
    | MultiServerMCPClient     |<---------->| MCP Server Trigger /mcp/toolbox|
    |   transport: streamable  |            |   +-- get_order_status (Code) |
    +-----------+--------------+            |   +-- days_until       (Code) |
                v                           +-------------------------------+
     create_agent(tools = n8n tools)

Concepts:
  * Hybrid pattern: n8n owns integrations (400+ nodes, OAuth credentials,
    retries); LangGraph owns the reasoning. Swap the Code tools for a Gmail,
    HubSpot or Postgres node and the agent code does not change.
  * The MCP Server Trigger node turns any tool nodes connected to it into an
    MCP server; the workflow must be *published* for the /mcp/ URL to work.
  * Remote MCP over streamable HTTP (demo 14 used a local stdio process).
  * Setup: see README "Deploy" (docker compose + import the workflow JSON).
"""
import asyncio
import logging
import os

from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient

from learn_langgraph import get_chat_model, header, save_mermaid

N8N_MCP_URL = os.getenv("N8N_MCP_URL", "http://localhost:5678/mcp/toolbox")
logging.getLogger("mcp.client.streamable_http").setLevel(logging.ERROR)  # n8n sends an extra SSE event

client = MultiServerMCPClient({"n8n": {"transport": "streamable_http", "url": N8N_MCP_URL}})


async def main() -> None:
    header(f"Tools served by the n8n workflow at {N8N_MCP_URL}")
    tools = await client.get_tools()
    for t in tools:
        print(f"  {t.name}: {t.description}")

    agent = create_agent(
        model=get_chat_model(),
        tools=tools,
        system_prompt="Use the tools for order data and date maths. Answer in one short sentence.",
    )
    save_mermaid(agent, "15_n8n_mcp_tools")

    header("Agent chaining two n8n tools")
    question = "When does order A100 arrive, and how many days from today is that?"
    result = await agent.ainvoke({"messages": [("user", question)]})
    for msg in result["messages"]:
        msg.pretty_print()


if __name__ == "__main__":
    asyncio.run(main())
