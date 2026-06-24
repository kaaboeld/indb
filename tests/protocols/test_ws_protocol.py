"""
WebSocket Protocol Tests for INDB

Tests WebSocket server functionality:
- Connection establishment
- Message sending/receiving
- Subscriptions
- ACK/NACK handling
- Error handling
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from protocols.ws_server import WSConnection, WSConnectionManager
from core.indb import INDB
from core.kernel import INDBKernel
from auth.manager import AuthManager


class MockWebSocket:
    """Mock WebSocket for testing"""
    
    def __init__(self):
        self.sent_messages = []
        self.received_messages = []
        self.closed = False
    
    async def accept(self):
        """Accept connection"""
        pass
    
    async def send_json(self, data):
        """Send JSON message"""
        self.sent_messages.append(data)
    
    async def receive_text(self):
        """Receive text message"""
        if self.received_messages:
            return self.received_messages.pop(0)
        raise asyncio.TimeoutError()
    
    async def close(self):
        """Close connection"""
        self.closed = True


@pytest.fixture
def mock_websocket():
    """Create mock WebSocket"""
    return MockWebSocket()


@pytest.fixture
def kernel():
    """Create INDB kernel"""
    db = INDB()
    kernel = INDBKernel()
    kernel.initialize(db)
    return kernel


@pytest.fixture
def auth_manager():
    """Create auth manager"""
    return AuthManager()


@pytest.fixture
def connection_manager(kernel, auth_manager):
    """Create connection manager"""
    return WSConnectionManager(kernel, auth_manager)


@pytest.mark.asyncio
class TestWSConnection:
    """Test WebSocket connection class"""
    
    async def test_connection_creation(self, mock_websocket):
        """Test creating a WebSocket connection"""
        conn = WSConnection(mock_websocket, "test-id")
        
        assert conn.connection_id == "test-id"
        assert conn.subscriptions == []
        assert conn.pending_messages == {}
        assert conn.last_activity > 0
    
    async def test_send_message_with_ack(self, mock_websocket):
        """Test sending message with ACK requirement"""
        conn = WSConnection(mock_websocket, "test-id")
        
        message = {"type": "test", "data": "hello"}
        ack_id = await conn.send_message(message, require_ack=True)
        
        # Check message was sent
        assert len(mock_websocket.sent_messages) == 1
        sent = mock_websocket.sent_messages[0]
        assert sent["type"] == "test"
        assert sent["data"] == "hello"
        assert "ack_id" in sent
        
        # Check pending messages
        assert ack_id in conn.pending_messages
        assert conn.pending_messages[ack_id]["retry_count"] == 0
    
    async def test_send_message_without_ack(self, mock_websocket):
        """Test sending message without ACK requirement"""
        conn = WSConnection(mock_websocket, "test-id")
        
        message = {"type": "test"}
        ack_id = await conn.send_message(message, require_ack=False)
        
        # Check message was sent
        assert len(mock_websocket.sent_messages) == 1
        
        # Check no pending messages
        assert ack_id not in conn.pending_messages
    
    async def test_acknowledge_message(self, mock_websocket):
        """Test acknowledging a message"""
        conn = WSConnection(mock_websocket, "test-id")
        
        # Send message with ACK
        ack_id = await conn.send_message({"type": "test"}, require_ack=True)
        assert ack_id in conn.pending_messages
        
        # Acknowledge
        conn.acknowledge(ack_id)
        assert ack_id not in conn.pending_messages
    
    async def test_retry_pending_messages(self, mock_websocket):
        """Test retrying unacknowledged messages"""
        conn = WSConnection(mock_websocket, "test-id")
        
        # Send message
        ack_id = await conn.send_message({"type": "test"}, require_ack=True)
        
        # Manually set sent_at to past
        import time
        conn.pending_messages[ack_id]["sent_at"] = time.time() - 10
        
        # Retry
        await conn.retry_pending(timeout=5.0)
        
        # Check message was resent
        assert len(mock_websocket.sent_messages) == 2
        assert conn.pending_messages[ack_id]["retry_count"] == 1


@pytest.mark.asyncio
class TestWSConnectionManager:
    """Test WebSocket connection manager"""
    
    async def test_connect(self, connection_manager, mock_websocket):
        """Test connecting a WebSocket"""
        connection_id = await connection_manager.connect(mock_websocket)
        
        assert connection_id in connection_manager.connections
        assert connection_manager.connections[connection_id].websocket == mock_websocket
    
    async def test_disconnect(self, connection_manager, mock_websocket):
        """Test disconnecting a WebSocket"""
        connection_id = await connection_manager.connect(mock_websocket)
        assert connection_id in connection_manager.connections
        
        connection_manager.disconnect(connection_id)
        assert connection_id not in connection_manager.connections
    
    async def test_handle_ack_message(self, connection_manager, mock_websocket):
        """Test handling ACK message"""
        connection_id = await connection_manager.connect(mock_websocket)
        conn = connection_manager.connections[connection_id]
        
        # Send a message that requires ACK
        ack_id = await conn.send_message({"type": "test"}, require_ack=True)
        assert ack_id in conn.pending_messages
        
        # Handle ACK
        await connection_manager.handle_message(connection_id, {
            "type": "ack",
            "ack_id": ack_id
        })
        
        # Check message was acknowledged
        assert ack_id not in conn.pending_messages
    
    async def test_handle_subscribe_message(self, connection_manager, mock_websocket):
        """Test handling subscribe message"""
        connection_id = await connection_manager.connect(mock_websocket)
        conn = connection_manager.connections[connection_id]
        
        # Subscribe
        await connection_manager.handle_message(connection_id, {
            "type": "subscribe",
            "query": {"location": "Amsterdam"}
        })
        
        # Check subscription was added
        assert len(conn.subscriptions) == 1
        assert conn.subscriptions[0] == {"location": "Amsterdam"}
        
        # Check response was sent
        assert len(mock_websocket.sent_messages) > 0
        response = mock_websocket.sent_messages[-1]
        assert response["type"] == "subscribed"
    
    async def test_handle_query_message(self, connection_manager, mock_websocket):
        """Test handling query message"""
        connection_id = await connection_manager.connect(mock_websocket)
        
        # Add some test data (Await ingestion)
        await connection_manager.kernel.db.ingest(["test", "data"], location="Test")
        
        # Query
        await connection_manager.handle_message(connection_id, {
            "type": "query",
            "query": {},
            "request_id": "test-123"
        })
        
        # Check response was sent
        assert len(mock_websocket.sent_messages) > 0
        response = mock_websocket.sent_messages[-1]
        assert response["type"] == "query_response"
        assert "data" in response
        assert response["request_id"] == "test-123"
    
    async def test_broadcast_event(self, connection_manager, mock_websocket):
        """Test broadcasting event to all connections"""
        # Connect multiple clients
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        
        await connection_manager.connect(ws1)
        await connection_manager.connect(ws2)
        
        # Broadcast event
        event = {"id": "123", "data": "test"}
        await connection_manager.broadcast_event(event)
        
        # Check all clients received the event
        assert len(ws1.sent_messages) > 0
        assert len(ws2.sent_messages) > 0
        
        assert ws1.sent_messages[-1]["type"] == "event"
        assert ws1.sent_messages[-1]["data"] == event
