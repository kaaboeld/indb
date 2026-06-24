import pytest
from pydantic import ValidationError
from core.event import Event
from core.models import EventCreate
from core.kernel import INDBKernel
from core.indb import INDB

@pytest.fixture
def kernel(monkeypatch, tmp_path):
    # Use temporary database file for test isolation
    test_db = tmp_path / "test_indb.bin"
    monkeypatch.setattr("storage.binary.DB_FILE", str(test_db))
    
    k = INDBKernel()
    # Reset db for test
    # Refactored INDB now requires Services
    from services.interpretation.cognitive_firewall import CognitiveFirewall
    from services.interpretation.engine import JITRenderer
    
    k.db = INDB(raft_node=None)
    # Re-inject JIT renderer if missing (though INDB init should satisfy this, 
    # but kernel init replaces memory stream)
    k.initialize(k.db)
    return k

def test_black_box_contract_requires_location():
    """blind_payload without location must be rejected."""
    with pytest.raises(ValidationError, match="Black Box Contract"):
        EventCreate(
            raw_data_anchor=["test"],
            location="",
            blind_payload="secret"
        )


def test_black_box_contract_requires_nonempty_location():
    """blind_payload with whitespace-only location must be rejected."""
    with pytest.raises(ValidationError, match="Black Box Contract"):
        EventCreate(
            raw_data_anchor=["test"],
            location="   ",
            blind_payload="secret"
        )


def test_black_box_contract_passes_with_location_and_timestamp():
    """blind_payload with valid location and timestamp must be accepted."""
    event = EventCreate(
        raw_data_anchor=["test"],
        location="vault/personal",
        blind_payload="secret",
        timestamp=1741219285.0
    )
    assert event.blind_payload == "secret"
    assert event.location == "vault/personal"
    assert event.timestamp == 1741219285.0


def test_no_blind_payload_location_still_required():
    """location remains required even without blind_payload."""
    with pytest.raises(ValidationError):
        EventCreate(raw_data_anchor=["test"], location=None)


@pytest.mark.asyncio
async def test_blind_payload_persistence(kernel):
    """Verify blind payload is stored and retrieved EXACTLY as is."""
    secret_data = "SUPER_SECRET_KEY_IV_123"
    
    from core.kernel import AuthContext
    auth = AuthContext("api_writer")
    
    event = await kernel.create_event({
        "raw_data_anchor": ["test", "event"],
        "location": "vault",
        "blind_payload": secret_data
    }, auth=auth)
    
    assert event["blind_payload"] == secret_data
    
    # Retrieve from memory check
    stored_event = kernel.db.memory[-1]
    assert stored_event.blind_payload == secret_data

@pytest.mark.asyncio
async def test_blind_payload_opacity(kernel):
    """Verify blind payload is NOT used in interpretation/keywords."""
    import time
    # This payload contains keywords that WOULD trigger specific emotions/narratives if analyzed
    # "pain" triggers negative/fear in kernel.py
    dangerous_payload = "pain blood scream"
    
    event_data = {
        "raw_data_anchor": ["safe", "context"],
        "location": "lab",
        "blind_payload": dangerous_payload
    }
    
    
    # Create Auth
    from core.kernel import InterpretRequest, AuthContext
    auth = AuthContext(user_id="api_writer")

    # Create event
    await kernel.create_event(event_data, auth=auth)
    
    # Interpret it
    request = InterpretRequest(context={"mood": "Neutral"})
    
    response = kernel.interpret(request, auth)
    interpreted_event = response["data"]["events"][-1]
    
    # Check Derived Emotion
    # "safe", "context" should be Neutral/Positive
    # If "pain" was read, it would become "Fear" or similar
    assert interpreted_event["derived_emotion"] == "Neutral"
    
    # Ensure payload is still attached
    assert interpreted_event["data"]["blind_payload"] == dangerous_payload

