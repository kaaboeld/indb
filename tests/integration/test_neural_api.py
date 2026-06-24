from fastapi.testclient import TestClient
from main import app
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

client = TestClient(app)

def test_neural_patterns():
    # Debug: Print all routes
    for route in app.routes:
        if hasattr(route, "path") and "neural" in route.path:
            print(f"FOUND ROUTE: {route.path}")

    response = client.get("/api/v2/fusion/neural/patterns")
    print(f"Response: {response.status_code} {response.json()}")
    assert response.status_code == 200
    json_resp = response.json()
    assert json_resp["status"] == "success"
    data = json_resp["data"]
    assert "patterns" in data or "error" in data
    
if __name__ == "__main__":
    test_neural_patterns()
