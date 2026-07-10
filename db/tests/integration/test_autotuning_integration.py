import pytest
import asyncio
from core.indb import INDB
from core.event import Event
from core.kernel import INDBKernel
import time

@pytest.mark.asyncio
async def test_autotuning_integration(tmp_path, monkeypatch):
    # Use temp db
    test_db = tmp_path / "tuning_integration.bin"
    monkeypatch.setattr("storage.binary.DB_FILE", str(test_db))
    
    # Initialize Core
    k = INDBKernel()
    k.db = INDB(raft_node=None)
    k.initialize(k.db)
    
    # Verify init
    assert hasattr(k.db, "_last_tune_time")
    assert k.db._last_tune_time == 0.0
    
    # Set threshold manually to check for changes
    k.db.fusion_engine.config["threshold"] = 0.85
    
    # Mock Analytics to return high CPU
    original_get_health = k.db.analytics.get_system_health
    k.db.analytics.get_system_health = lambda: {
        "cpu_percent": 95.0, 
        "memory_percent": 10.0
    }
    
    # Create event (should trigger tuning because last_tune_time is 0 and now > 0)
    # Wait, check logic: (now - 0) > 5.0 is True.
    # So first event should trigger tuning.
    
    from core.kernel import AuthContext
    auth = AuthContext("api_writer")
    
    await k.create_event({"raw_data_anchor": ["test"]}, auth)
    
    # Check if threshold increased (High CPU > 80% -> +0.05 capped at 0.95)
    # 0.85 -> 0.90
    assert k.db.fusion_engine.config["threshold"] > 0.85
    assert k.db.fusion_engine.config["threshold"] == 0.90
    
    # Verify last_tune_time updated
    assert k.db._last_tune_time > 0.0
    
    # Restore
    k.db.analytics.get_system_health = original_get_health
