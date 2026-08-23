
import pytest
from fastapi.testclient import TestClient
from main import app
from core.models import StandardResponse

client = TestClient(app)

def test_health_check_v2():
    response = client.get("/api/v2/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "data" in data
    assert "meta" in data
    assert data["data"]["project"]["name"] == "INDB"
    assert "version" in data["data"]["project"]

def test_create_event_v2():
    payload = {
        "raw_data_anchor": ["test", "token"],
        "location": "TestCity",
        "ttl": 3600
    }
    response = client.post("/api/v2/events", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["location"] == "TestCity"
    assert set(data["data"]["raw_data_anchor"]) == set(["test", "token"])
    assert "id" in data["data"]

def test_list_events_v2_pagination():
    # Create a few events first
    for i in range(5):
        client.post("/api/v2/events", json={
            "raw_data_anchor": [f"event_{i}"],
            "location": "PaginationCity"
        })
    
    # Test default limit
    response = client.get("/api/v2/events")
    assert response.status_code == 200
    data = response.json()
    assert "pagination" in data["meta"]
    
    # Test offset and limit
    response = client.get("/api/v2/events?limit=2&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) <= 2
    assert data["meta"]["pagination"]["limit"] == 2

def test_interpret_events_v2():
    payload = {
        "context": {"mood": "Neutral"},
        "limit": 5
    }
    response = client.post("/api/v2/interpret", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "events" in data["data"]
    assert "context_mood" in data["data"]
    assert "performance" in data["meta"]

def test_fusion_stats_v2():
    response = client.get("/api/v2/fusion/stats")
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data["data"]
    assert "metrics" in data["data"]

def test_analytics_overview_v2():
    response = client.get("/api/v2/analytics/overview")
    assert response.status_code == 200
    data = response.json()
    assert "database" in data["data"]
    assert "fusion" in data["data"]
