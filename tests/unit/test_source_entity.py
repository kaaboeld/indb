import pytest
from core.kernel import INDBKernel, AuthContext
from core.indb import INDB
from core.source import SourceType

@pytest.fixture
def kernel(monkeypatch, tmp_path):
    test_db = tmp_path / "test_source.bin"
    monkeypatch.setattr("storage.binary.DB_FILE", str(test_db))
    
    k = INDBKernel()
    k.db = INDB(raft_node=None)
    k.initialize(k.db)
    return k

@pytest.mark.asyncio
async def test_source_registration_and_linkage(kernel):
    """
    Verify that we can register a source and link events to it.
    """
    # 1. Admin Auth (Required for SYSTEM_CONFIG)
    admin_auth = AuthContext(user_id="admin_user")
    
    # 2. Register a Trusted Sensor
    source_data = kernel.register_source(
        name="Precise Temp Sensor 01",
        source_type="sensor",
        reputation=0.95,
        auth=admin_auth
    )
    
    source_id = source_data["id"]
    assert source_id is not None
    assert source_data["reputation"] == 0.95
    assert source_data["type"] == "sensor"
    
    # 3. Ingest Event linked to Source
    # Using API Writer for ingest
    writer_auth = AuthContext(user_id="api_writer")
    
    event_payload = {
        "raw_data_anchor": ["temp", "24.5", "stable"],
        "location": "lab_1",
        "source_id": source_id
    }
    
    event_res = await kernel.create_event(event_payload, auth=writer_auth)
    
    # 4. Verification
    assert event_res["source_id"] == source_id
    
    # Verify internal retrieval
    stored_source = kernel.db.get_source(source_id)
    assert stored_source.name == "Precise Temp Sensor 01"
    assert stored_source.type == SourceType.SENSOR

@pytest.mark.asyncio
async def test_source_registration_permission_denied(kernel):
    """
    Verify that standard writers cannot register sources.
    """
    writer_auth = AuthContext(user_id="api_writer")
    
    with pytest.raises(PermissionError) as exc:
        kernel.register_source(
            name="Rogue Bot",
            source_type="agent",
            auth=writer_auth
        )
    assert "Access Denied" in str(exc.value)
