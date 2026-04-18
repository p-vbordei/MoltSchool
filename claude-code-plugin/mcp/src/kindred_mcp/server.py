"""stdio MCP server exposing kin_ask and kin_contribute.

Launched by Claude Code as `uv run --directory <plugin>/mcp python -m kindred_mcp.server`.
Reads/writes JSON-RPC frames on stdin/stdout; do not print to stdout.
"""
from __future__ import annotations

import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from kindred_mcp.tools import (
    kin_ask,
    kin_ask_tool,
    kin_contribute,
    kin_contribute_tool,
)

app: Server = Server("kindred")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [kin_ask_tool(), kin_contribute_tool()]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "kin_ask":
        result = await kin_ask(**arguments)
    elif name == "kin_contribute":
        result = await kin_contribute(**arguments)
    else:
        raise ValueError(f"unknown tool: {name}")
    return [TextContent(type="text", text=result)]


async def main() -> None:
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
