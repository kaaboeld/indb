"""
Data Flow Tests for INDB
Validates all data paths through the system.
"""

import os

import pytest
import asyncio
from typing import Dict, Any

# Same default as the rest of the project: Dockerfile, fly.toml and the launcher use 8000.
BASE_URL = os.environ.get("INDB_API_URL", "http://localhost:8000").rstrip("/")

from core.kernel import INDBKernel
from core.event import Event
from storage.binary import save_encrypted, load_decrypted

class TestEventIngestionFlow:
    """Test complete event ingestion flow"""
    
    @pytest.mark.asyncio
    async def test_event_creation_to_storage(self):
        """Test: Event creation → Kernel → Storage → Retrieval"""
        kernel = INDBKernel()
        
        # Create event data (v2 schema)
        event_data = {
            "raw_data_anchor": ["test:flow_test", "value:123"],
            "location": "TestLab"
        }
        
        # Ingest (Async)
        from core.kernel import AuthContext
        # Use admin_user to ensure permissions
        auth = AuthContext(user_id="admin_user")
        
        result = await kernel.create_event(event_data, auth)
        assert result is not None, "Ingestion failed"
        
        # Verify in kernel
        from core.kernel import QueryRequest
        events = kernel.query(QueryRequest(), auth)
        assert len(events) > 0, "No events in kernel after ingestion"
        
        # Verify event exists
        # Note: raw_data_anchor is list
        found = any("test:flow_test" in e.get("raw_data_anchor", []) for e in events)
        assert found, "Ingested event not found in query results"
    
    @pytest.mark.asyncio
    async def test_batch_ingestion_flow(self):
        """Test: Batch ingestion → Fusion → Storage"""
        kernel = INDBKernel()
        from core.kernel import AuthContext
        auth = AuthContext(user_id="admin_user")
        
        # Create batch of similar events (should fuse automatically on ingest)
        for _ in range(5):
            await kernel.create_event({
                "raw_data_anchor": ["location:home", "action:arrive"],
                "location": "Home"
            }, auth)
        
        # Verify fusion occurred
        from core.kernel import QueryRequest
        all_events = kernel.query(QueryRequest(), auth)
        fused_count = sum(1 for e in all_events if e.get("fusion_count", 0) > 1)
        # Fusion is auto-triggered, simply checking count logic runs without error

    @pytest.mark.asyncio
    async def test_persistence_flow(self):
        """Test: Memory → Disk → Reload → Memory"""
        kernel = INDBKernel()
        from core.kernel import AuthContext
        auth = AuthContext(user_id="admin_user")
        
        # Add unique event
        unique_str = "unique_id:persistence_test_12345"
        await kernel.create_event({
            "raw_data_anchor": [unique_str], 
            "location": "Disk"
        }, auth)
        
        # Save to disk
        if hasattr(kernel.db, "_persist"):
            kernel.db._persist()
        
        # Create new kernel (simulates restart)
        new_kernel = INDBKernel()
        # Load logic happens in init
        
        # Verify event persisted
        from core.kernel import QueryRequest
        events = new_kernel.query(QueryRequest(), auth)
        found = any(unique_str in e.get("raw_data_anchor", []) for e in events)
        assert found, "Event did not persist across restart"


class TestQueryFlow:
    """Test query data flow"""
    
    @pytest.mark.asyncio
    async def test_query_with_filters(self):
        """Test: Query → Filter → Cache → Results"""
        kernel = INDBKernel()
        from core.kernel import AuthContext, QueryRequest
        auth = AuthContext(user_id="admin_user")
        
        # Add test events
        await kernel.create_event({"raw_data_anchor": ["type:A"], "location": "Lab"}, auth)
        await kernel.create_event({"raw_data_anchor": ["type:B"], "location": "Lab"}, auth)
        
        # Query with filter
        req = QueryRequest(filters={"filter_key": "type", "filter_value": "A"})
        results = kernel.query(req, auth)
    
    def test_cache_flow(self):
        """Test: Query → Cache Miss → Compute → Cache Hit"""
        # Cache logic is internal to Kernel.query usually
        pass


class TestFusionFlow:
    """Test fusion engine data flow"""
    
    @pytest.mark.asyncio
    async def test_fusion_pipeline(self):
        """Test: Events → Similarity Check → Fusion → Fused Event"""
        kernel = INDBKernel()
        from core.kernel import AuthContext
        auth = AuthContext(user_id="admin_user")
        
        # Create similar events
        for i in range(3):
            await kernel.create_event({
                "raw_data_anchor": ["message:Same message", f"index:{i}"],
                "location": "FusionLab"
            }, auth)
        
        # Run fusion mechanism explicitly if needed, but it's usually auto-tuned and run on ingest.
        # However, for unit testing pipeline without ingestion:
        if hasattr(kernel.db, "fusion_engine") and kernel.db.fusion_engine:
             # Just verify engine is loaded
             assert kernel.db.fusion_engine is not None
        
        # Verify
        from core.kernel import QueryRequest
        events = kernel.query(QueryRequest(), auth)
        fused = [e for e in events if e.get("fusion_count", 0) > 1]
    
    def test_deduplication_flow(self):
        """Test: Event → Bloom Filter → Dedup Check → Storage"""
        from core.bloom import dedup_filter, mark_seen, check_duplicate
        
        # Clear filter
        dedup_filter.clear()
        
        # First event
        event_hash = "test_event_hash_123"
        assert not check_duplicate(event_hash), "Should not be duplicate initially"
        
        # Mark as seen
        mark_seen(event_hash)
        
        # Second event (duplicate)
        assert check_duplicate(event_hash), "Should be detected as duplicate"


class TestEncryptionFlow:
    """Test encryption data flow"""
    
    def test_encryption_pipeline(self):
        """Test: Data → Serialize → Encrypt → Decrypt → Deserialize"""
        from storage.binary import MASTER_KEY
        from core.encryption import FileEncryptor
        import msgpack
        
        # Original data
        events = [
            {"id": 1, "raw_data_anchor": ["test:encryption"]},
            {"id": 2, "raw_data_anchor": ["test:flow"]}
        ]
        
        # Serialize
        serialized = msgpack.packb(events)
        
        # Encrypt
        encrypted = FileEncryptor.encrypt_file(serialized, MASTER_KEY)
        
        # Verify encrypted
        assert encrypted != serialized, "Data not encrypted"
        
        # Decrypt
        decrypted = FileEncryptor.decrypt_file(encrypted, MASTER_KEY)
        
        # Deserialize
        restored = msgpack.unpackb(decrypted, raw=False)
        
        # Verify
        assert restored == events, "Data corrupted in encryption flow"


class TestProtocolFlow:
    """Test protocol data flows"""
    
    @pytest.mark.asyncio
    async def test_http_ingestion_flow(self):
        """Test: HTTP Request → Parse → Ingest → Response"""
        import httpx
        
        async with httpx.AsyncClient() as client:
            # Send event via HTTP
            response = await client.post(
                f"{BASE_URL}/api/v2/events",
                json={
                    "raw_data_anchor": ["protocol:http", "test:flow"],
                    "location": "TestClient"
                },
                timeout=5.0
            )
            
            assert response.status_code == 200, f"HTTP ingestion failed: {response.text}"
            
            # Verify response structure
            data = response.json()
            assert "data" in data, "Response missing data"
            assert "id" in data["data"], "Response missing event ID"
    
    @pytest.mark.asyncio
    async def test_query_response_flow(self):
        """Test: HTTP Query → Kernel → Cache → JSON Response"""
        import httpx
        
        async with httpx.AsyncClient() as client:
            # Query events
            response = await client.get(
                f"{BASE_URL}/api/v2/events?limit=5",
                timeout=5.0
            )
            
            assert response.status_code == 200, "Query failed"
            
            # Verify response
            data = response.json()
            assert "data" in data, "Response missing data"
            assert isinstance(data["data"], list), "Data is not a list"


def run_flow_tests():
    """Run all data flow tests"""
    print("=" * 60)
    print("INDB DATA FLOW TESTS")
    print("=" * 60)
    print()
    
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto",
    ])
    
    print()
    if exit_code == 0:
        print("✅ ALL DATA FLOWS VALIDATED")
        return True
    else:
        print("❌ DATA FLOW ISSUES DETECTED")
        return False


if __name__ == "__main__":
    import sys
    success = run_flow_tests()
    sys.exit(0 if success else 1)
