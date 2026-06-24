#!/usr/bin/env python3
"""Explore INDB data with interesting queries."""

import httpx
import json

BASE = "https://indb-node-1.backend.orb.local"
client = httpx.Client(verify=False, timeout=30.0, follow_redirects=True)

def fmt(events):
    for e in events:
        loc = e.get("location", "?")
        tags = ", ".join(e.get("raw_data_anchor", [])[:8])
        print(f"  📍 [{loc}]  {tags}")

def search(q, label, limit=4):
    print(f"\n{'─'*65}")
    print(f"🔍  SEMANTIC SEARCH: {label}")
    print(f"    query: \"{q}\"")
    r = client.get(f"{BASE}/api/v2/search", params={"q": q, "limit": limit})
    if r.status_code == 200:
        data = r.json().get("data", [])
        print(f"    → {len(data)} results")
        fmt(data)
    else:
        print(f"    ⚠️  HTTP {r.status_code}: {r.text[:120]}")

def interpret(mood, goal, label, limit=4):
    print(f"\n{'─'*65}")
    print(f"🧠  JIT INTERPRET: {label}")
    print(f"    mood={mood}, goal={goal}")
    r = client.post(f"{BASE}/api/v2/interpret",
                    json={"context": {"mood": mood, "goal": goal}, "limit": limit})
    if r.status_code == 200:
        data = r.json().get("data", [])
        print(f"    → {len(data)} results")
        fmt(data)
    else:
        print(f"    ⚠️  HTTP {r.status_code}: {r.text[:120]}")

def filter_events(key, value, label, limit=5):
    print(f"\n{'─'*65}")
    print(f"🗂️   FILTER: {label}")
    print(f"    {key}={value}")
    r = client.get(f"{BASE}/api/v2/events",
                   params={"filter_key": key, "filter_value": value, "limit": limit})
    if r.status_code == 200:
        data = r.json().get("data", [])
        print(f"    → {len(data)} results (showing {min(len(data), limit)})")
        fmt(data[:limit])
    else:
        print(f"    ⚠️  HTTP {r.status_code}: {r.text[:120]}")

def fusion_stats():
    print(f"\n{'─'*65}")
    print(f"⚡  FUSION STATS")
    r = client.get(f"{BASE}/api/v2/fusion/stats")
    if r.status_code == 200:
        d = r.json().get("data", {})
        for k, v in d.items():
            print(f"  {k:30s}: {v}")
    else:
        print(f"    ⚠️  HTTP {r.status_code}: {r.text[:120]}")

def analytics():
    print(f"\n{'─'*65}")
    print(f"📊  ANALYTICS OVERVIEW")
    r = client.get(f"{BASE}/api/v2/analytics/overview")
    if r.status_code == 200:
        d = r.json().get("data", {})
        db = d.get("database", {})
        fus = d.get("fusion", {})
        sys_h = d.get("system_health", {})
        print(f"  Total events     : {db.get('total_events', '?'):,}")
        print(f"  Fusion rate      : {fus.get('fusion_rate', 0):.1f}%")
        print(f"  Unique locations : {db.get('unique_locations', '?')}")
        print(f"  Health score     : {d.get('health_score', '?')}")
        print(f"  Memory RSS       : {sys_h.get('memory_rss_mb', 0):.0f} MB")
        top = db.get("top_locations", {})
        print(f"\n  Top locations:")
        for loc, cnt in sorted(top.items(), key=lambda x: -x[1]):
            bar = "█" * (cnt // 50)
            print(f"    {cnt:5,}  {bar}  {loc}")
    else:
        print(f"    ⚠️  HTTP {r.status_code}: {r.text[:120]}")


print("=" * 65)
print("  INDB DATA EXPLORATION")
print("=" * 65)

# Overview first
analytics()
fusion_stats()

# --- Semantic searches across different book themes ---
search("obsession whale sea monster captain", "Moby Dick themes")
search("sin redemption lord shall", "Biblical themes")
search("beauty portrait corruption youth soul", "Dorian Gray themes")
search("revolution freedom poor suffering mercy", "Les Misérables themes")
search("river adventure freedom slave", "Huckleberry Finn themes")

# --- JIT Interpretation with different moods ---
interpret("Philosopher", "WisdomOfAges", "Philosopher seeking wisdom")
interpret("Explorer", "Adventure", "Explorer seeking adventure")
interpret("Preacher", "MoralLesson", "Preacher seeking moral lessons")
interpret("Detective", "Clue", "Detective looking for clues/secrets")

# --- Location-based filtering ---
filter_events("location", "London, England", "Events from London")
filter_events("location", "Nantucket, Massachusetts, USA", "Events from Nantucket (Moby Dick)")
filter_events("location", "Jerusalem, Israel", "Events from Jerusalem (Bible)")

print(f"\n{'='*65}")
print("  DONE")
print(f"{'='*65}\n")
client.close()
