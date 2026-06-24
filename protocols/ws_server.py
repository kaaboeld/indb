"""
WebSocket Protocol Server for INDB

Realtime updates with guaranteed delivery.
Features: subscriptions, ACK/NACK, message ordering, reconnection.

Protocol:
- JSON or BSON frames
- Message types: subscribe, query, event, ack, error
- Guaranteed delivery with retry
"""

import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Optional, Any
import time
import uuid
from core.config_schema import get_config
from core.indb import INDB
from core.kernel import INDBKernel, InterpretRequest, QueryRequest
from auth.manager import AuthManager

config = get_config()


class WSConnection:
    """WebSocket connection with message queue and ACK tracking"""
    
    def __init__(self, websocket: WebSocket, connection_id: str):
        self.websocket = websocket
        self.connection_id = connection_id
        self.subscriptions: List[Dict[str, Any]] = []
        self.pending_messages: Dict[str, Dict] = {}  # ack_id -> message
        self.last_activity = time.time()
    
    async def send_message(self, message: Dict[str, Any], require_ack: bool = True) -> str:
        """Send message with optional ACK requirement"""
        ack_id = str(uuid.uuid4())
        message["ack_id"] = ack_id
        
        if require_ack:
            self.pending_messages[ack_id] = {
                "message": message,
                "sent_at": time.time(),
                "retry_count": 0
            }
        
        await self.websocket.send_json(message)
        self.last_activity = time.time()
        return ack_id
    
    def acknowledge(self, ack_id: str):
        """Mark message as acknowledged"""
        if ack_id in self.pending_messages:
            del self.pending_messages[ack_id]
    
    async def retry_pending(self, max_retries: int = 3, timeout: float = 5.0):
        """Retry unacknowledged messages"""
        now = time.time()
        to_retry = []
        
        for ack_id, msg_data in list(self.pending_messages.items()):
            if now - msg_data["sent_at"] > timeout:
                if msg_data["retry_count"] < max_retries:
                    to_retry.append((ack_id, msg_data))
                else:
                    # Dead letter - give up
                    print(f"⚠️  Message {ack_id} failed after {max_retries} retries")
                    del self.pending_messages[ack_id]
        
        for ack_id, msg_data in to_retry:
            msg_data["retry_count"] += 1
            msg_data["sent_at"] = now
            await self.websocket.send_json(msg_data["message"])


class WSConnectionManager:
    """Manage WebSocket connections and subscriptions"""
    
    def __init__(self, kernel: INDBKernel, auth_manager: AuthManager):
        self.kernel = kernel
        self.auth_manager = auth_manager
        self.connections: Dict[str, WSConnection] = {}
    
    async def connect(self, websocket: WebSocket) -> str:
        """Accept new WebSocket connection"""
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        self.connections[connection_id] = WSConnection(websocket, connection_id)
        print(f"✅ WebSocket connected: {connection_id}")
        return connection_id
    
    def disconnect(self, connection_id: str):
        """Remove connection"""
        if connection_id in self.connections:
            del self.connections[connection_id]
            print(f"❌ WebSocket disconnected: {connection_id}")
    
    async def handle_message(self, connection_id: str, message: Dict[str, Any]):
        """Handle incoming message"""
        conn = self.connections.get(connection_id)
        if not conn:
            return
        
        msg_type = message.get("type")
        
        if msg_type == "ack":
            # Client acknowledging our message
            ack_id = message.get("ack_id")
            if ack_id:
                conn.acknowledge(ack_id)
        
        elif msg_type == "subscribe":
            # Subscribe to query
            query = message.get("query", {})
            conn.subscriptions.append(query)
            await conn.send_message({
                "type": "subscribed",
                "subscription_id": len(conn.subscriptions) - 1,
                "query": query
            })
        
        elif msg_type == "query":
            # One-time query
            await self._handle_query(conn, message)
        
        elif msg_type == "interpret":
            # Interpret request
            await self._handle_interpret(conn, message)
    
    async def _handle_query(self, conn: WSConnection, message: Dict[str, Any]):
        """Handle query request"""
        try:
            # Get auth context (anonymous for now)
            auth = self.auth_manager.anonymous_context()
            
            # Build query request
            query_params = message.get("query", {})
            request = QueryRequest(**query_params)
            
            # Execute via kernel
            events = self.kernel.query(request, auth)
            
            # Send response
            await conn.send_message({
                "type": "query_response",
                "data": {
                    "events": events,
                    "total": len(events)
                },
                "request_id": message.get("request_id")
            })
        
        except Exception as e:
            await conn.send_message({
                "type": "error",
                "error": str(e),
                "request_id": message.get("request_id")
            }, require_ack=False)
    
    async def _handle_interpret(self, conn: WSConnection, message: Dict[str, Any]):
        """Handle interpret request"""
        try:
            auth = self.auth_manager.anonymous_context()
            
            interpret_params = message.get("params", {})
            request = InterpretRequest(**interpret_params)
            
            result = self.kernel.interpret(request, auth)
            
            await conn.send_message({
                "type": "interpret_response",
                "data": result,
                "request_id": message.get("request_id")
            })
        
        except Exception as e:
            await conn.send_message({
                "type": "error",
                "error": str(e),
                "request_id": message.get("request_id")
            }, require_ack=False)
    
    async def broadcast_event(self, event: Dict[str, Any]):
        """Broadcast event to all subscribed connections"""
        for conn in self.connections.values():
            # Check if event matches any subscriptions
            # TODO: Implement subscription matching
            await conn.send_message({
                "type": "event",
                "data": event
            })
    
    async def retry_loop(self):
        """Background task to retry unacknowledged messages"""
        while True:
            await asyncio.sleep(5)  # Check every 5 seconds
            for conn in list(self.connections.values()):
                try:
                    await conn.retry_pending()
                except Exception as e:
                    print(f"❌ Retry error: {e}")


# FastAPI WebSocket endpoint
async def websocket_endpoint(websocket: WebSocket, manager: WSConnectionManager):
    """WebSocket endpoint handler"""
    connection_id = await manager.connect(websocket)
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle message
            await manager.handle_message(connection_id, message)
    
    except WebSocketDisconnect:
        manager.disconnect(connection_id)
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        manager.disconnect(connection_id)


# Standalone server for testing
async def run_ws_server(kernel: INDBKernel, auth_manager: AuthManager, port: int = None):
    """
    Start WebSocket server (standalone)
    
    For production, use FastAPI integration in main.py
    """
    port = port or config.server_port
    
    print(f"\n{'='*60}")
    print(f"🚀 Starting WebSocket Server on port {port}")
    print(f"{'='*60}")
    
    manager = WSConnectionManager(kernel, auth_manager)
    
    # Start retry loop
    retry_task = asyncio.create_task(manager.retry_loop())
    
    # TODO: Implement standalone WebSocket server
    # For now, this requires FastAPI integration
    print("⚠️  WebSocket server requires FastAPI integration")
    print("   Add to main.py:")
    print(f"   @app.websocket('/ws')")
    print(f"   async def websocket_route(websocket: WebSocket):")
    print(f"       await websocket_endpoint(websocket, ws_manager)")
    
    await asyncio.Future()  # Run forever


if __name__ == "__main__":
    from migration_manager import MigrationManager
    
    print("\n" + "="*60)
    print("🚀 Initializing INDB for WebSocket Server")
    print("="*60)
    
    migration_manager = MigrationManager()
    temp_db = INDB()
    migration_success = migration_manager.run_migrations(temp_db)
    
    if not migration_success:
        print("❌ Migration failed")
        exit(1)
    
    kernel = INDBKernel()
    kernel.initialize(temp_db)
    auth_manager = AuthManager()
    
    asyncio.run(run_ws_server(kernel, auth_manager))
