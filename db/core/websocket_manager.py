"""
WebSocket Connection Manager.

Handles active connections, subscriptions, and event broadcasting.
"""
import time
from typing import Dict, Any, Optional, List
from fastapi import WebSocket

from core.models import WebSocketSubscription

class ConnectionManager:
    """
    Enhanced WebSocket connection manager with authentication and subscriptions.
    
    Features:
    - JWT authentication support
    - Per-connection subscription filters
    - Selective event broadcasting
    - Connection metadata tracking
    """

    def __init__(self):
        self.active_connections: Dict[WebSocket, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, user_id: Optional[str] = None):
        """Accept connection and store metadata."""
        await websocket.accept()
        self.active_connections[websocket] = {
            "user_id": user_id,
            "connected_at": time.time(),
            "subscription": WebSocketSubscription(),
            "message_count": 0,
        }

    def disconnect(self, websocket: WebSocket):
        """Remove connection."""
        if websocket in self.active_connections:
            del self.active_connections[websocket]

    def update_subscription(self, websocket: WebSocket, subscription: WebSocketSubscription):
        """Update subscription filters for a connection."""
        if websocket in self.active_connections:
            self.active_connections[websocket]["subscription"] = subscription

    async def broadcast(self, message: str, event_type: str = "all", location: Optional[str] = None):
        """
        Broadcast message to subscribed connections.
        
        Args:
            message: JSON message to broadcast
            event_type: Type of event (new_event, batch_complete, etc.)
            location: Event location for filtering
        """
        for connection, metadata in list(self.active_connections.items()):
            try:
                subscription = metadata["subscription"]
                
                # Check if connection is subscribed to this event type
                if "all" not in subscription.event_types and event_type not in subscription.event_types:
                    continue
                
                # Check location filter
                if subscription.locations and location:
                    if not any(loc.lower() in location.lower() for loc in subscription.locations):
                        continue
                
                # Send message
                await connection.send_text(message)
                metadata["message_count"] += 1
                
            except Exception as e:
                # Connection broken, remove it
                self.disconnect(connection)

    async def send_personal(self, websocket: WebSocket, message: str):
        """Send message to specific connection."""
        if websocket in self.active_connections:
            try:
                await websocket.send_text(message)
                self.active_connections[websocket]["message_count"] += 1
            except Exception:
                self.disconnect(websocket)

    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            "total_connections": len(self.active_connections),
            "authenticated_users": sum(1 for m in self.active_connections.values() if m["user_id"]),
            "total_messages_sent": sum(m["message_count"] for m in self.active_connections.values()),
        }

# Global Singleton
manager = ConnectionManager()
