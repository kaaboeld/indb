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
            
            # If interaction failed or returned raw Response, skip negotiation
            if isinstance(response, Response) and response.media_type != "application/json":
                return response
            
            # Get Accept header
            accept_header = request.headers.get("accept", "application/json")
            
            # Handle MessagePack format
            if "application/msgpack" in accept_header or "application/x-msgpack" in accept_header:
                if isinstance(response, JSONResponse):
                    # Deserialize JSON body to dict
                    content_dict = json.loads(response.body)
                    
                    # Inject format metadata
                    if isinstance(content_dict, dict) and "meta" in content_dict:
                        if content_dict["meta"] is None:
                            content_dict["meta"] = {}
                        content_dict["meta"]["format"] = "msgpack"
                    
                    return MessagePackResponse(content=content_dict)
            
            # Default JSON processing
            if isinstance(response, JSONResponse):
                content_dict = json.loads(response.body)
                # Inject format metadata
                if isinstance(content_dict, dict) and "meta" in content_dict:
                    if content_dict["meta"] is None:
                        content_dict["meta"] = {}
                    content_dict["meta"]["format"] = "json"
                
                # Re-render JSON with new metadata
                return JSONResponse(content=content_dict, status_code=response.status_code)
                
            return response

        return custom_route_handler
