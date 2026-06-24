#!/usr/bin/env python3
"""
INDB mechanics verification: fusion, storage, events.

- Fusion: threshold, strategies, compression rate
- Storage: persistence, event structure
- Event mechanics: raw_data_anchor, location, temporal
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

INDB_URL = os.environ.get("INDB_API_URL", "http://localhost:8888")
REPORT_DIR = Path(__file__).resolve().parent.parent / "reports"


def http_get(path: str) -> Dict:
    import urllib.request
    req = urllib.request.Request(f"{INDB_URL}{path}", headers={"User-Agent": "indb-workflow"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def verify_health() -> Dict[str, Any]:
    """Health and database stats."""
    data = http_get("/api/v2/health")["data"]
    db = data["database"]
    return {
        "total_events": db["total_events"],
        "fused_events": db.get("fused_events", db["total_events"]),
        "fusion_rate": db["fusion_rate"],
        "storage_efficiency": db.get("storage_efficiency", "N/A"),
    }


def verify_analytics() -> Dict[str, Any]:
    """Analytics overview."""
    try:
        data = http_get("/api/v2/analytics/overview")["data"]
        return {
            "performance": data.get("performance", {}),
            "database": data.get("database", {}),
        }
    except Exception as e:
        return {"error": str(e)}


def verify_events_sample(limit: int = 200) -> Dict[str, Any]:
    """Sample events: structure, fusion flags, locations."""
    data = http_get(f"/api/v2/events?limit={limit}")["data"]
    fused_count = sum(1 for e in data if e.get("is_fused"))
    locations = Counter(e.get("location", "?") for e in data)
    sources = Counter(str(e.get("location", "")).split("/")[0].split(":")[0] for e in data if e.get("location"))
    return {
        "sample_size": len(data),
        "fused_in_sample": fused_count,
        "top_locations": locations.most_common(15),
        "top_sources": sources.most_common(10),
        "sample_events": [
            {"id": e["id"][:8], "location": e.get("location"), "is_fused": e.get("is_fused"), "fusion_count": e.get("fusion_count", 0)}
            for e in data[:5]
        ],
    }


def verify_fusion_mechanics() -> Dict[str, Any]:
    """Fusion-specific checks."""
    data = http_get("/api/v2/events?limit=500")["data"]
    fused = [e for e in data if e.get("is_fused")]
    high_fusion = [e for e in data if (e.get("fusion_count") or 0) > 1]
    return {
        "total_sampled": len(data),
        "fused_count": len(fused),
        "high_fusion_count": len(high_fusion),
        "fusion_examples": [
            {"id": e["id"][:8], "fusion_count": e.get("fusion_count"), "location": e.get("location")}
            for e in high_fusion[:5]
        ],
    }


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    results = {
        "health": verify_health(),
        "analytics": verify_analytics(),
        "events_sample": verify_events_sample(),
        "fusion_mechanics": verify_fusion_mechanics(),
    }
    out = REPORT_DIR / "MECHANICS_VERIFICATION.json"
    with open(out, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
