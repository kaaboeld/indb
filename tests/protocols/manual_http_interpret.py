"""
HTTP Interpretation Tests

Tests for HTTP interpretation endpoint.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import requests
import json


BASE_URL = "http://localhost:8000"


def test_http_interpret_basic():
    """Test basic HTTP interpretation request."""
    print("\n🧪 Test: HTTP Basic Interpretation")
    
    request = {
        "context": {"mood": "High_Value"},
        "limit": 5
    }
    
    response = requests.post(f"{BASE_URL}/api/v2/interpret", json=request)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "data" in data
    assert "events" in data["data"]
    assert len(data["data"]["events"]) <= 5
    
    print(f"✅ Received {len(data['data']['events'])} events")
    print(f"   First event: {data['data']['events'][0]['location'] if data['data']['events'] else 'none'}")


def test_http_interpret_with_temporal():
    """Test HTTP interpretation with temporal query."""
    print("\n🧪 Test: HTTP Temporal Interpretation")
    
    request = {
        "context": {"mood": "Neutral"},
        "temporal_query": "summer",
        "limit": 10
    }
    
    response = requests.post(f"{BASE_URL}/api/v2/interpret", json=request)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "data" in data
    assert "events" in data["data"]
    print(f"✅ Received {len(data['data']['events'])} summer events")


def test_http_interpret_real_data():
    """Test that HTTP returns real data from indb.bin."""
    print("\n🧪 Test: HTTP Real Data")
    
    request = {
        "context": {"mood": "Neutral"},
        "limit": 20
    }
    
    response = requests.post(f"{BASE_URL}/api/v2/interpret", json=request)
    
    assert response.status_code == 200
    data = response.json()
    
    # Should have real events
    assert len(data["data"]["events"]) > 0
    
    # Check event structure
    event = data["data"]["events"][0]
    assert "id" in event
    assert "location" in event
    assert "tokens" in event or "raw_data_anchor" in event
    
    print(f"✅ Real data verified: {len(data['data']['events'])} events")
    print(f"   Locations: {set(e['location'] for e in data['data']['events'][:5])}")


def run_all_tests():
    """Run all HTTP tests."""
    print("\n" + "=" * 60)
    print("🧪 HTTP Interpretation Tests")
    print("=" * 60)
    
    try:
        test_http_interpret_basic()
        test_http_interpret_with_temporal()
        test_http_interpret_real_data()
        
        print("\n✅ All HTTP tests passed!")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    run_all_tests()
