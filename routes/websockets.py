"""
WebSocket Routes (v2)

Handles real-time event streaming and subscription management.
"""
import json
import time
from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends

from core.models import StandardResponse, WebSocketSubscription
from core.websocket_manager import manager
from core.kernel import AuthContext
from auth.manager import AuthManager

router = APIRouter() # No prefix for /ws, but can have tags

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = Query(None)):
    """
    Real-time event stream (v2).
    
    Supports:
    - Filters (subscription updates)
    - Authentication (query param or header)
    """
    user_id = "anonymous"
    if token:
        # Validate token (Basic stub)
        # In real world: valid = auth_manager.verify_token(token)
        if token.startswith("sk_"):
             user_id = "api_user"
    
    await manager.connect(websocket, user_id=user_id)
    
    try:
        # Send welcome message
        welcome_msg = {
            "type": "control", 
            "message": "Connected to INDB v2 Stream",
            "connection_id": str(id(websocket))
        }
        await manager.send_personal(websocket, json.dumps(welcome_msg))
        
        while True:
            # Wait for client messages (Subscriptions/Heartbeats)
            data = await websocket.receive_text()
            
            try:
                payload = json.loads(data)
                msg_type = payload.get("type")
                
                if msg_type == "subscribe":
                    # Update filters
                    subscription = WebSocketSubscription(**payload.get("data", {}))
                    manager.update_subscription(websocket, subscription)
                    
                    response = {"type": "control", "status": "subscribed", "filters": subscription.dict()}
                    await manager.send_personal(websocket, json.dumps(response))
                    
                elif msg_type == "ping":
                     response = {"type": "pong", "timestamp": time.time()}
                     await manager.send_personal(websocket, json.dumps(response))
                     
                else:
                    # Echo or ignore
                    pass
                    
            except json.JSONDecodeError:
                pass
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WS Error: {e}")
        manager.disconnect(websocket)


@router.get("/api/v2/websocket/stats", response_model=StandardResponse[Dict[str, Any]], tags=["websocket"])
async def get_websocket_stats():
    """
    Get WebSocket connection statistics (v2).
    
    Returns information about active connections, authentication status,
    and message counts.
    """
    stats = manager.get_stats()
    
    # Add detailed connection info
    connections_detail = []
    for ws, metadata in manager.active_connections.items():
        connections_detail.append({
            "user_id": metadata["user_id"],
            "authenticated": metadata["user_id"] is not None,
            "connected_at": metadata["connected_at"],
            "message_count": metadata["message_count"],
            "subscription": metadata["subscription"].dict()
        })
        
    data = {
        "overview": stats,
        "connections": connections_detail
    }
    
    return StandardResponse(data=data)
