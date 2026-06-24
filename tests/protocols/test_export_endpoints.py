
import pytest
import json
import csv
import io
from fastapi.testclient import TestClient
from pathlib import Path
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from main import app
from services.query.advanced_filter import FilterCriteria

@pytest.fixture
def client():
    return TestClient(app)

class TestExportEndpoints:
    def test_query_endpoint(self, client):
        # 1. Create some events
        client.post("/api/v2/events", json={"raw_data_anchor": ["filter_me"], "location": "TestCity"})
        client.post("/api/v2/events", json={"raw_data_anchor": ["ignore_me"], "location": "OtherCity"})
        
        # 2. Query
        criteria = {
            "field": "location",
            "op": "eq",
            "value": "TestCity"
        }
        
        response = client.post("/api/v2/events/query", json=criteria)
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) >= 1
        assert data["data"][0]["location"] == "TestCity"

    def test_export_json(self, client):
        # Create event
        client.post("/api/v2/events", json={"raw_data_anchor": ["export_json"], "location": "JSONCity"})
        
        # Filter for it
        criteria = json.dumps({
            "field": "location",
            "op": "eq",
            "value": "JSONCity"
        })
        
        response = client.get(f"/api/v2/export/json?filters={criteria}")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        
        content = response.json()
        assert isinstance(content, list)
        found = False
        for item in content:
            if item.get("location") == "JSONCity":
                found = True
                break
        assert found

    def test_export_csv(self, client):
        # Create event
        client.post("/api/v2/events", json={"raw_data_anchor": ["export_csv"], "location": "CSVCity"})
        
        # Filter for it
        criteria = json.dumps({
            "field": "location",
            "op": "eq",
            "value": "CSVCity"
        })
        
        response = client.get(f"/api/v2/export/csv?filters={criteria}")
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        
        # Parse CSV
        content = response.text
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        
        found = False
        for row in rows:
            if row["location"] == "CSVCity":
                found = True
                assert "export_csv" in row["tokens"]
                break
        assert found
