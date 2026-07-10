#!/usr/bin/env python3
"""
Test MCP SSE client connection — debug why Hermes fails.
Run: python scripts/test_mcp_client.py
"""
import asyncio
import sys

# Use backend's mcp (in Docker or venv)
try:
    from mcp.client.sse import sse_client
    from mcp import ClientSession
except ImportError:
    print("Install: pip install mcp httpx httpx-sse")
    sys.exit(1)


async def test(url: str):
    print(f"Connecting to {url} ...")
    try:
        async with sse_client(url, timeout=10, sse_read_timeout=30) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                print(f"OK! Tools: {[t.name for t in tools.tools]}")
    except Exception as e:
        print(f"FAIL: {type(e).__name__}: {e}")
        if hasattr(e, "exceptions") and e.exceptions:
            for i, sub in enumerate(e.exceptions):
                print(f"  Sub {i}: {type(sub).__name__}: {sub}")
        raise


if __name__ == "__main__":
    url = "http://localhost:8888/api/v2/mcp/sse"
    if len(sys.argv) > 1:
        url = sys.argv[1]
    asyncio.run(test(url))
