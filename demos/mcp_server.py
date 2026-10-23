"""A tiny MCP server used by demo 14 (not a lesson on its own).

It speaks the Model Context Protocol over stdio, so any MCP client (Claude
Code, Claude Desktop, or LangChain via langchain-mcp-adapters) can use its tools.
Try it in the official inspector:  npx @modelcontextprotocol/inspector uv run demos/mcp_server.py
"""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("toolbox")


@mcp.tool()
def celsius_to_fahrenheit(celsius: float) -> float:
    """Convert a temperature from Celsius to Fahrenheit."""
    return round(celsius * 9 / 5 + 32, 1)


@mcp.tool()
def word_count(text: str) -> int:
    """Count the words in a text."""
    return len(text.split())


if __name__ == "__main__":
    mcp.run(transport="stdio")  # stdout carries the protocol: never print() here
