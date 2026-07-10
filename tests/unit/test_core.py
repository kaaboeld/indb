"""
Comprehensive Unit Tests for INDB Core

Tests Event, TTLCache, and INDB core functionality.
"""

import sys
import time
import pytest
import asyncio
from core import Event, TTLCache, INDB


class TestEvent:
    """Test Event model."""
    
    def test_event_creation(self):
        """Test basic event creation."""
        event = Event(
            raw_data_anchor=["test", "event"],
            location="TestLab"
        )
        
        assert event.id is not None
        assert len(event.id) > 0
        assert event.raw_data_anchor == ["test", "event"]
        assert event.location == "TestLab"
        assert event.timestamp > 0
    
    def test_event_with_custom_id(self):
        """Test event with custom ID."""
        custom_id = "custom-123"
        event = Event(
            raw_data_anchor=["test"],
            location="Lab",
            id=custom_id
        )
        
        assert event.id == custom_id
    
    def test_event_to_dict(self):
        """Test event serialization."""
        event = Event(
            raw_data_anchor=["bicycle", "speed"],
            location="Amsterdam"
        )
        
        data = event.to_dict()
        
        assert "id" in data
        assert "timestamp" in data
        assert "raw_data_anchor" in data
        assert "location" in data
        assert data["raw_data_anchor"] == ["bicycle", "speed"]
        assert data["location"] == "Amsterdam"
    
    def test_event_from_dict(self):
        """Test event deserialization."""
        data = {
            "id": "test-123",
            "timestamp": 1234567890.0,
            "raw_data_anchor": ["test", "data"],
            "location": "TestLocation",
            "ttl": 3600
        }
        
        event = Event.from_dict(data)
        
        assert event.id == "test-123"
        assert event.timestamp == 1234567890.0
        assert event.raw_data_anchor == ["test", "data"]
        assert event.location == "TestLocation"
        assert event.ttl == 3600
    
    def test_event_repr(self):
        """Test event string representation."""
        event = Event(
            raw_data_anchor=["a", "b", "c"],
            location="Lab"
        )
        
        repr_str = repr(event)
        assert "Event" in repr_str
        assert "tokens=3" in repr_str
        assert "location=Lab" in repr_str


class TestTTLCache:
    """Test TTLCache."""
    
    def test_cache_set_get(self):
        """Test basic cache operations."""
        cache = TTLCache()
        
        cache.set("key1", "value1", ttl=60)
        value = cache.get("key1")
        
        assert value == "value1"
    
    def test_cache_expiry(self):
        """Test cache TTL expiration."""
        cache = TTLCache()
        
        cache.set("key1", "value1", ttl=1)
        time.sleep(1.1)
        value = cache.get("key1")
        
        assert value is None
    
    def test_cache_missing_key(self):
        """Test getting non-existent key."""
        cache = TTLCache()
        value = cache.get("nonexistent")
        
        assert value is None
    
    def test_cache_delete(self):
        """Test cache deletion."""
        cache = TTLCache()
        
        cache.set("key1", "value1")
        deleted = cache.delete("key1")
        value = cache.get("key1")
        
        assert deleted is True
        assert value is None
    
    def test_cache_clear(self):
        """Test cache clearing."""
        cache = TTLCache()
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None
    
    def test_cache_size(self):
        """Test cache size tracking."""
        cache = TTLCache()
        
        assert cache.size() == 0
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        assert cache.size() == 2
    
    def test_cache_cleanup_expired(self):
        """Test cleanup of expired entries."""
        cache = TTLCache()
        
        cache.set("key1", "value1", ttl=1)
        cache.set("key2", "value2", ttl=60)
        
        time.sleep(1.1)
        removed = cache.cleanup_expired()
        
        assert removed == 1
        assert cache.size() == 1


@pytest.mark.asyncio
class TestINDB:
    """Test INDB core functionality."""
    
    async def test_indb_initialization(self):
        """Test INDB initialization."""
        db = INDB()
        
        assert db is not None
        assert hasattr(db, 'memory')
        assert hasattr(db, 'cache')
    
    async def test_indb_ingest_event(self):
        """Test event ingestion."""
        db = INDB()
        initial_count = len(db.memory)
        
        # Use correct ingest API
        # Disable fusion to ensure append
        if db.fusion_engine:
            db.fusion_engine.config["enabled"] = False
            
        await db.ingest(
            raw_data_anchor=[f"unique_test_{time.time()}", "ingest"],
            location="TestLab"
        )
        
        assert len(db.memory) == initial_count + 1
    
    async def test_indb_scan_all(self):
        """Test scanning all events."""
        db = INDB()
        
        # Ingest test events
        for i in range(5):
            await db.ingest(
                raw_data_anchor=[f"test{i}"],
                location="Lab"
            )
        
        # Scan all events (no filter)
        results = db.scan("", "", context_mood="Neutral")
        
        assert len(results) >= 5
    
    async def test_indb_scan_with_context(self):
        """Test context-aware scanning."""
        db = INDB()
        
        await db.ingest(
            raw_data_anchor=["bicycle", "speed"],
            location="Amsterdam"
        )
        
        # Scan with context mood
        results = db.scan("", "", context_mood="High_Value")
        
        assert len(results) > 0
    
    async def test_indb_persistence(self):
        """Test save and load."""
        db = INDB()
        
        await db.ingest(
            raw_data_anchor=["persist", "test"],
            location="Lab"
        )
        
        # Should auto-save
        # Create new instance and load
        db2 = INDB()
        
        # Should have loaded data
        assert len(db2.memory) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
