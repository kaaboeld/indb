import httpx
import json
import time

BASE_URL = "http://localhost:8000"
client = httpx.Client(base_url=BASE_URL, timeout=30.0, follow_redirects=True)

def print_example(title, method, endpoint, payload):
    print(f"\n{'#'*80}")
    print(f"# EXAMPLE: {title}")
    print(f"{'#'*80}")
    
    print(f"\n--- REQUEST ---")
    print(f"{method} {endpoint}")
    print(f"Content-Type: application/json")
    print(json.dumps(payload, indent=2))
    
    try:
        response = client.request(method, endpoint, json=payload)
        print(f"\n--- RESPONSE (Status: {response.status_code}) ---")
        
        try:
            data = response.json()
            # Truncate lists for readability in report if too long
            if 'data' in data and 'events' in data['data']:
                events = data['data']['events']
                if len(events) > 2:
                    data['data']['events'] = events[:2] + [{"...": f"({len(events)-2} more events truncated for brevity)"}]
            
            if 'data' in data and 'lens_view' in data['data']:
                 view = data['data']['lens_view']
                 if len(view) > 2:
                     data['data']['lens_view'] = view[:2] + [{"...": f"({len(view)-2} more events truncated)"}]

            print(json.dumps(data, indent=2))
        except:
            print(response.text)
            
    except Exception as e:
        print(f"ERROR: {e}")

def run():
    print("Generating COMPLEX INDB API Analysis...")
    
    # 1. Fusion Analysis (Data Reduction)
    print("\n" + "="*80)
    print("ANALYSIS SECTION 1: FUSION METRICS")
    print("="*80)
    # We simulate a "Fusion Report" by scanning everything and aggregating client-side (since API is raw)
    # real world this would be an aggregation endpoint
    try:
        resp = client.post("/api/v2/interpret", json={"limit": 5000})
        data = resp.json()
        events = data['data']['events']
        total = len(events)
        fused = [e for e in events if e.get('is_fused') or e.get('fusion_count', 0) > 0]
        
        print(f"\n[METRICS]")
        print(f"Total Raw Events Ingested: {total}")
        print(f"Fused (Deduplicated) Events: {len(fused)}")
        if fused:
            print(f"Example Fused Event: {json.dumps(fused[0], indent=2)}")
        else:
            print("No significant fusion detected yet (corpus is highly unique).")
            
    except Exception as e:
        print(f"Metrics Error: {e}")

    # 2. Comparative Lens Analysis
    print("\n" + "="*80)
    print("ANALYSIS SECTION 2: CONTEXTUAL LENS IMPACT")
    print("="*80)
    print("Comparing different Lens configurations on the SAME dataset...\n")

    # Scenario A: Balanced View (50% Simple / 50% Complex)
    print_example(
        "Scenario A: Balanced View (Simple vs High Frequency)",
        "POST",
        "/api/v2/lens/query",
        {
            "context_a": "simple",
            "context_b": "high_frequency", 
            "ratio": [0.5, 0.5],
            "limit": 3
        }
    )

    # Scenario B: Heavily Biased (90% Simple)
    print_example(
        "Scenario B: Biased View (90% Simple Focus)",
        "POST",
        "/api/v2/lens/query",
        {
            "context_a": "simple",
            "context_b": "high_frequency", 
            "ratio": [0.9, 0.1],
            "limit": 3
        }
    )
    
    # 3. Targeted Retrieval
    print("\n" + "="*80)
    print("ANALYSIS SECTION 3: COMPLEX SELECTION")
    print("="*80)
    
    # Try to find specific Dostoevsky content with metadata
    print_example(
        "Targeted Selection: Dostoevsky's 'Crime and Punishment'",
        "POST",
        "/api/v2/interpret",
        {
            "limit": 3,
            "query_mode": "filter", # forcing usage if supported or ignored fallback
            "context": {"mood": "Dostoevsky"}, # simulating context injection
            "filter_key": "location", # trying to hint selection
            "filter_value": "Dostoevsky" 
        }
    )

    # 4. System Stats
    print_example("Cluster Health & Metadata", "GET", "/health", {})

if __name__ == "__main__":
    run()
