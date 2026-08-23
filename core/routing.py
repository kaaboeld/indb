"""
Content Negotiation Routing

Intercepts requests to handle multiple response formats (JSON, MessagePack)
based on the Accept header.

AUTONOMOUS: Uses msgpack instead of BSON (no external database dependencies)
"""

from typing import Callable, Any
from fastapi import Request, Response
from fastapi.routing import APIRoute
from fastapi.responses import JSONResponse
import json
import msgpack
from pydantic import BaseModel

class MessagePackResponse(Response):
    """MessagePack binary response (autonomous alternative to BSON)"""
    media_type = "application/msgpack"

    def render(self, content: Any) -> bytes:
        return msgpack.packb(content, use_bin_type=True)

def _holds_json_body(response: Any) -> bool:
    """True for a fully rendered JSON body that can be re-serialised."""
    if not isinstance(response, Response):
        return False
    media_type = response.media_type or response.headers.get("content-type", "")
    if "application/json" not in media_type:
        return False
    return bool(getattr(response, "body", None))


def _carried_headers(response: Response) -> dict:
    """
    Headers of the original response, minus the ones re-rendering invalidates.

    Rebuilding the response would otherwise drop everything the endpoint set on it —
    rate limit counters among them — because a fresh Response starts with none.
    """
    dropped = {"content-length", "content-type"}
    return {k: v for k, v in response.headers.items() if k.lower() not in dropped}


class ContentNegotiationRoute(APIRoute):
    """
    Custom API Route that handles Content Negotiation.
    
    - Checks 'Accept' header.
    - If 'application/msgpack', serializes response as MessagePack.
    - Default is JSON.
    - Injects 'format' metadata into standard responses.
    
    AUTONOMOUS: No external database dependencies (msgpack is pure Python serialization)
    """
    
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()
        
        async def custom_route_handler(request: Request) -> Response:
            # Execute original handler
            response = await original_route_handler(request)

            # Recognised by content type rather than response class: an endpoint that
            # declares a response_model is served through a fast path that returns a plain
            # Response holding JSON bytes, so checking for JSONResponse would miss almost
            # every route. Streams (CSV export, SSE) carry no .body and pass through.
            if not _holds_json_body(response):
                return response

            content = json.loads(response.body)
            accept_header = request.headers.get("accept", "application/json")
            wants_msgpack = (
                "application/msgpack" in accept_header
                or "application/x-msgpack" in accept_header
            )

            if isinstance(content, dict) and "meta" in content:
                if content["meta"] is None:
                    content["meta"] = {}
                content["meta"]["format"] = "msgpack" if wants_msgpack else "json"

            response_class = MessagePackResponse if wants_msgpack else JSONResponse
            return response_class(
                content=content,
                status_code=response.status_code,
                headers=_carried_headers(response),
                background=response.background,
            )

        return custom_route_handler
