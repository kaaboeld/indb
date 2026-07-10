import httpx
import json

BASE_URL = "http://localhost:8000"

def run_query(desc, payload):
    print(f"\n--- {desc} ---")
    try:
        resp = httpx.post(f"{BASE_URL}/api/v2/interpret", json=payload, timeout=10.0)
        data = resp.json()
        print(f"Events found: {len(data['data'].get('events', []))}")
        for evt in data['data'].get('events', [])[:3]:
            anchor = evt.get('raw_data_anchor', [])
            loc = evt.get('location', 'unknown')
            print(f"  - {anchor} @ {loc}")
    except Exception as e:
        print(f"Error: {e}")

def run_lens(desc, payload):
    print(f"\n--- LENS: {desc} ---")
    try:
        resp = httpx.post(f"{BASE_URL}/api/v2/lens/query", json=payload, timeout=10.0)
        data = resp.json()
        if 'data' in data:
             meta = data['data'].get('metadata', {})
             print(f"Lens Count: {meta.get('lens_count')} (H1: {meta.get('h1_count')}, H2: {meta.get('h2_count')})")
             for evt in data['data'].get('lens_view', [])[:3]:
                 anchor = evt.get('raw_data_anchor', [])
                 loc = evt.get('location', 'unknown')
                 print(f"  - {anchor} @ {loc}")
        else:
            print(f"No data: {data}")
    except Exception as e:
        print(f"Error: {e}")

# 1. Verify Dostoevsky Data
print("\n--- Verifying Dostoevsky Data ---")
try:
    # Fetch scan of events (no filter, but we filter in client)
    resp = httpx.post(f"{BASE_URL}/api/v2/interpret", 
                      json={"limit": 1000, "context": {"mood": "Neutral"}}, 
                      timeout=30.0)
    data = resp.json()
    events = data['data'].get('events', [])
    
    # Filter for Dostoevsky
    dostoevsky_events = [
        e for e in events 
        if "Dostoevsky" in e.get("original_location", "")
    ]
    
    print(f"Total events scanned: {len(events)}")
    
    print(f"Total events scanned: {len(events)}")
    
    print("--- First 5 Events ---")
    for e in events[:5]:
        loc = e.get("original_location") or e.get("location")
        print(f"  - Location: {loc}")

    print("--- Last 5 Events ---")
    for e in events[-5:]:
        loc = e.get("original_location") or e.get("location")
        print(f"  - Location: {loc}")

    # lens query...

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

# 2. Verify Tolstoy Data
print("\n--- Verifying Tolstoy Data ---")
try:
    tolstoy_events = []
    for e in events:
        loc = e.get("original_location") or e.get("location") or ""
        if "Tolstoy" in str(loc):
            tolstoy_events.append(e)
            
    print(f"Tolstoy events found: {len(tolstoy_events)}")
    for evt in tolstoy_events[:5]:
        data_dict = evt.get('data', evt)
        anchor = data_dict.get('raw_data_anchor', [])
        loc = evt.get('original_location') or evt.get('location') or 'unknown'
        print(f"  - {anchor} @ {loc}")
except Exception as e:
    print(f"Error: {e}")

# 3. Lens Query
run_lens("Lens: Mixed View", {
    "context_a": "all",
    "context_b": "all",
    "ratio": [0.5, 0.5],
    "limit": 5
})
