"""
INDB MCP Server — Model Context Protocol.

Supports:
- Streamable HTTP (Hermes, modern clients) — POST/GET at /mcp
- Legacy SSE (older clients) — GET /mcp/sse, POST /mcp/messages/
"""
from typing import Any, Dict, List
import json

from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.responses import Response
from starlette.requests import Request

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.server.transport_security import TransportSecuritySettings
from mcp import types

from core.instance import indb
from core.kernel import AuthContext, QueryRequest
from core.constants import INTERPRET_MOOD_DEFAULT

# Streamable HTTP (Hermes uses this)
_STREAMABLE_AVAILABLE = False
try:
    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
    _STREAMABLE_AVAILABLE = True
except ImportError:
    pass

# MCP Server Instance
mcp_server = Server("indb-mcp")

# Transport with permissive security for localhost (Hermes, Cursor, etc.)
_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=False,
    allowed_hosts=["localhost", "127.0.0.1", "indb-loadbalancer", "indb-node-1"],
    allowed_origins=[
        "http://localhost:8888", "http://127.0.0.1:8888",
        "http://localhost", "http://127.0.0.1", "null",
    ],
)
sse_transport = SseServerTransport("/messages/", security_settings=_security)


@mcp_server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="query_events",
            description="Query events from INDB. filter_key='location' + filter_value for location substring. filter_key=word (e.g. epistemology, memory) with filter_value='' to search event content by token.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filter_key": {"type": "string", "description": "location, temporal, or a token word to search in content"},
                    "filter_value": {"type": "string", "description": "Filter value; empty for token search"},
                    "mood": {"type": "string", "description": "Context mood (e.g. Fear, Joy, Neutral)"},
                    "limit": {"type": "integer", "default": 20},
                    "offset": {"type": "integer", "default": 0}
                }
            }
        ),
        types.Tool(
            name="ingest_event",
            description="Store a fact or summary in INDB. Use meaningful tokens: key words from the content. Location format: source/context (e.g. hermes://fetch/wikipedia-summary, hermes://user/request).",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Content tokens space separated (e.g. epistemology branch philosophy knowledge truth)"},
                    "location": {"type": "string", "description": "Event location e.g. hermes://source/context"},
                    "blind_payload": {"type": "string", "description": "Confidential payload (optional)"}
                },
                "required": ["content", "location"]
            }
        ),
        types.Tool(
            name="get_stats",
            description="Get database statistics",
            inputSchema={"type": "object"}
        )
    ]


@mcp_server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    if not arguments:
        arguments = {}

    if name == "query_events":
        query = QueryRequest(
            filter_key=arguments.get("filter_key"),
            filter_value=arguments.get("filter_value"),
            context_mood=arguments.get("mood") or INTERPRET_MOOD_DEFAULT,
            limit=arguments.get("limit", 10),
            offset=arguments.get("offset", 0)
        )
        events = indb.query(query, AuthContext(user_id="mcp-agent", auth_method="mcp"))

        serialized = []
        for e in events:
            d = e.to_dict() if hasattr(e, "to_dict") else e
            serialized.append(f"- ID: {d.get('id')}\n  Loc: {d.get('location')}\n  Data: {d.get('raw_data_anchor')}")

        text = "\n".join(serialized) if serialized else "No events found."
        return [types.TextContent(type="text", text=text)]

    elif name == "ingest_event":
        content = arguments.get("content", "").split()
        location = arguments.get("location")
        blind = arguments.get("blind_payload")

        event_data = {
            "raw_data_anchor": content,
            "location": location,
            "blind_payload": blind
        }

        res = await indb.create_event(event_data, AuthContext(user_id="mcp-agent"))
        return [types.TextContent(type="text", text=f"Ingested Event ID: {res['id']}")]

    elif name == "get_stats":
        stats = indb.db.get_stats()  # Full analytics (kernel.get_stats is minimal)
        clean_stats = {k: str(v) for k, v in stats.items()}
        return [types.TextContent(type="text", text=json.dumps(clean_stats, indent=2))]

    raise ValueError(f"Unknown tool: {name}")


async def handle_sse(request: Request) -> Response:
    """SSE connection handler — client connects here, gets endpoint for POST."""
    scope = dict(request.scope)
    # root_path from mount; fallback from request path
    rp = scope.get("root_path") or ""
    if not rp and "path" in scope:
        full = request.url.path
        if "/api/v2/mcp" in full:
            rp = "/api/v2/mcp"
        else:
            rp = "/mcp"
    scope["root_path"] = rp or "/mcp"
    try:
        async with sse_transport.connect_sse(
            scope, request.receive, request._send
        ) as streams:
            await mcp_server.run(
                streams[0], streams[1], mcp_server.create_initialization_options()
            )
    except ValueError:
        return Response("Request validation failed", status_code=400)
    return Response()


_sse_app: Starlette | None = None
_streamable_session_manager = None

if _STREAMABLE_AVAILABLE:
    _streamable_session_manager = StreamableHTTPSessionManager(
        app=mcp_server,
        json_response=True,  # Hermes works better with JSON
        stateless=True,  # No session tracking, simpler
        security_settings=_security,
    )


def _get_sse_app() -> Starlette:
    """Lazy-create SSE app (legacy)."""
    global _sse_app
    if _sse_app is None:
        _sse_app = Starlette(
            routes=[
                Route("/sse", endpoint=handle_sse, methods=["GET"]),
                Mount("/messages/", app=sse_transport.handle_post_message),
            ]
        )
    return _sse_app


async def _mcp_dispatch(scope: dict, receive, send):
    """Route: /sse, /messages/* → SSE; else → Streamable HTTP."""
    path = scope.get("path", "") or "/"
    if path.rstrip("/").endswith("/sse") or "/messages" in path:
        await _get_sse_app()(scope, receive, send)
    elif _streamable_session_manager:
        await _streamable_session_manager.handle_request(scope, receive, send)
    else:
        await _get_sse_app()(scope, receive, send)


def create_mcp_app() -> Starlette:
    """Combined MCP app: Streamable HTTP (Hermes) + legacy SSE."""
    if not _STREAMABLE_AVAILABLE:
        return _get_sse_app()
    return Starlette(routes=[Mount("/", app=_mcp_dispatch)])


def get_streamable_lifespan():
    """Return lifespan context for Streamable HTTP. Use in main app lifespan."""
    if _streamable_session_manager is None:
        return None
    return _streamable_session_manager.run()


# Legacy router for backwards compatibility (if any code imports it)
router = None  # Replaced by mount in app_factory
