"""Connect to a running DESi Workbench MCP server and verify its public tool surface."""
from __future__ import annotations

import argparse
import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


EXPECTED_TOOLS = {
    "get_capabilities",
    "start_review",
    "get_next_stage",
    "submit_stage",
    "finalize_review",
}


async def smoke(url: str) -> None:
    async with streamable_http_client(url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            response = await session.list_tools()
            names = {tool.name for tool in response.tools}
            missing = EXPECTED_TOOLS - names
            extra = names - EXPECTED_TOOLS
            if missing or extra:
                raise RuntimeError(
                    f"unexpected MCP tool surface; missing={sorted(missing)} extra={sorted(extra)}"
                )
            print("MCP_TRANSPORT_OK", ",".join(sorted(names)))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000/mcp")
    args = parser.parse_args()
    asyncio.run(smoke(args.url))


if __name__ == "__main__":
    main()
