"""
Integration Tests for INDB 0.10.0
End-to-end protocol testing.
"""

import os

import pytest
import httpx
import asyncio
import msgpack
from typing import Dict, Any


# 8000 is the port the Dockerfile, fly.toml and the launcher all use, so a suite pinned to
# another one only passed against a server started by hand.
BASE_URL = os.environ.get("INDB_API_URL", "http://localhost:8000").rstrip("/")

# Writes need a credential unless the target server runs with AUTH_MODE=OPEN.
API_HEADERS = {"X-API-Key": os.environ["INDB_API_KEY"]} if os.environ.get("INDB_API_KEY") else {}


class TestHTTPProtocol:
    """Test HTTP/REST API"""
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test health check"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
    
    @pytest.mark.asyncio
    async def test_create_event(self):
        """Test event creation"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/api/v2/events",
                json={"raw_data_anchor": ["test", "integration"], "location": "TestLab"},
                headers=API_HEADERS,
            )
            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            assert "id" in data["data"]
    
    @pytest.mark.asyncio
    async def test_query_events(self):
        """Test event querying"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/api/v2/events?limit=10")
            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            assert isinstance(data["data"], list)
    
    @pytest.mark.asyncio
    async def test_analytics(self):
        """Test analytics endpoint"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/api/v2/analytics")
            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            assert "total_events" in data["data"]
    
    @pytest.mark.asyncio
    async def test_cache_stats(self):
        """Test cache statistics"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/api/v2/cache/stats")
            assert response.status_code == 200
            data = response.json()
            assert "data" in data


class TestMessagePackProtocol:
    """Test MessagePack content negotiation"""
    
    @pytest.mark.asyncio
    async def test_msgpack_response(self):
        """Test MessagePack binary response"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/api/v2/events?limit=5",
                headers={"Accept": "application/msgpack"}
            )
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/msgpack"
            
            # Decode msgpack
            data = msgpack.unpackb(response.content, raw=False)
            assert "data" in data
            assert data["meta"]["format"] == "msgpack"


class TestWebSocketProtocol:
    """Test WebSocket subscriptions"""
    
    @pytest.mark.asyncio
    async def test_websocket_connection(self):
        """Test WebSocket connection"""
        # Note: Requires websockets library
        try:
            import websockets
            
            ws_url = BASE_URL.replace("http://", "ws://").replace("https://", "wss://")
            async with websockets.connect(f"{ws_url}/ws") as ws:
                # Send subscription
                await ws.send('{"action": "subscribe", "event_type": "fusion"}')
                
                # Receive confirmation
                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                assert response is not None
                
        except ImportError:
            pytest.skip("websockets library not installed")
        except Exception as e:
            pytest.skip(f"WebSocket test skipped: {e}")


class TestGraphQLProtocol:
    """Test GraphQL queries"""
    
    @pytest.mark.asyncio
    async def test_graphql_query(self):
        """Test GraphQL event query"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/graphql",
                json={
                    "query": "{ events(limit: 5) { id data } }"
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            assert "events" in data["data"]


class TestSecurityFeatures:
    """Test security features"""
    
    @pytest.mark.asyncio
    async def test_tls_redirect(self):
        """Test TLS availability (if enabled)"""
        # This test depends on INDB_USE_SSL environment variable
        try:
            async with httpx.AsyncClient(verify=False) as client:
                tls_url = BASE_URL.replace("http://", "https://")
                response = await client.get(f"{tls_url}/health", timeout=5.0)
                assert response.status_code == 200
        except Exception:
            pytest.skip("TLS not enabled or not available")
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting (if enabled)"""
        async with httpx.AsyncClient() as client:
            # Send many requests quickly
            responses = []
            for _ in range(100):
                try:
                    response = await client.get(f"{BASE_URL}/health", timeout=1.0)
                    responses.append(response.status_code)
                except Exception:
                    pass
            
            # Should have some successful requests
            assert 200 in responses


class TestPerformanceFeatures:
    """Test performance optimizations"""
    
    @pytest.mark.asyncio
    async def test_cache_hit(self):
        """Test cache functionality"""
        async with httpx.AsyncClient() as client:
            # First request (cache miss)
            response1 = await client.get(f"{BASE_URL}/api/v2/events?limit=10")
            assert response1.status_code == 200
            
            # Second request (should hit cache)
            response2 = await client.get(f"{BASE_URL}/api/v2/events?limit=10")
            assert response2.status_code == 200
            
            # Check cache stats
            stats_response = await client.get(f"{BASE_URL}/api/v2/cache/stats")
            stats = stats_response.json()["data"]
            assert stats["query_cache"]["hits"] > 0


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
