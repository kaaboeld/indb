import requests
import json
import sys
import os

# Load configuration
try:
    sys.path.insert(0, "..")
    from core.config import config
    BASE_URL = config.base_url
except ImportError:
    # Fallback for standalone execution
    HTTP_PORT = int(os.getenv("INDB_PORT", "8000"))
    BASE_URL = f"http://localhost:{HTTP_PORT}"

def run_query(title, payload):
    print(f"\n🔍 {title}")
    print(f"   Payload: {json.dumps(payload)}")
    
    try:
        response = requests.post(f"{BASE_URL}/api/v2/interpret", json=payload)
        response.raise_for_status()
        data = response.json()
        
        events = data.get("data", {}).get("events", [])
        print(f"   ✅ Found {len(events)} memories")
        
        for i, e in enumerate(events[:5]): # Show top 5
            tokens = e.get('tokens') or e.get('raw_data_anchor')
            is_fused = e.get('is_fused', False)
            fusion_count = e.get('fusion_count', 1)
            print(f"      {i+1}. [{e.get('location')}] (Fused: {is_fused}) -> {tokens}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

def main():
    print("="*60)
    print("🧠 INDB Query Examples")
    print("="*60)

    # 1. Contextual Query: What does a 'Driver' care about?
    # Expectation: Should prioritize 'traffic' related tokens or locations due to mood/context relevance
    # (Note: In this basic version, mood might just be metadata, but let's see)
    run_query("Context: Driver (Traffic Focus)", {
        "context": {"mood": "Driver"},
        "limit": 5
    })

    # 2. Contextual Query: What does an 'Analyst' see?
    # Expectation: Might see generic or all events, or specific cyber details
    run_query("Context: Analyst (Cyber/Office Focus)", {
        "context": {"mood": "Analyst"},
        "limit": 5
    })
    
    # 3. Keyword/Token Search (Using Dedicated Search Endpoint)
    # Finding memories with specific qualities
    print("\n🔍 Search: 'Blue' (Ocean/Calm)")
    try:
        # Note: Search endpoint is GET
        response = requests.get(f"{BASE_URL}/api/v2/search", params={"q": "blue", "limit": 5, "fuzzy": True})
        response.raise_for_status()
        data = response.json()
        
        # Search returns list of dicts directly in data
        events = data.get("data", [])
        print(f"   ✅ Found {len(events)} memories")
        
        for i, item in enumerate(events):
            e = item
            # Search endpoint structure is flat list of objects
            # matches = item.get('matches', [])
            tokens = e.get('raw_data_anchor') or e.get('tokens')
            is_fused = e.get('is_fused', False)
            print(f"      {i+1}. [{e.get('location')}] (Fused: {is_fused}) -> {tokens}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # 4. Fusion Inspector
    # Show that we are hitting fused events
    run_query("Fusion Inspection (All Events)", {
        "context": {"mood": "Inspector"},
        "limit": 50
    })

if __name__ == "__main__":
    main()
