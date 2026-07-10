#!/usr/bin/env python3
"""
REST-based INDB cycle: 5 back-and-forth requests (ingest → query → ingest → query → stats).
Mimics hermes_indb_cycle.sh via direct REST API when MCP is unavailable.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import urllib.request

INDB_URL = os.environ.get("INDB_API_URL", "http://localhost:8888")
BASE = f"{INDB_URL}/api/v2"


def req(method: str, path: str, body: dict | None = None) -> dict:
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    req_obj = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    with urllib.request.urlopen(req_obj, timeout=30) as r:
        return json.loads(r.read().decode())


def ingest(content: list[str], location: str) -> dict:
    return req("POST", "/events", {"raw_data_anchor": content, "location": location})


def query(filter_key: str = None, filter_value: str = None, limit: int = 20) -> list:
    params = [f"limit={limit}"]
    if filter_key:
        params.append(f"filter_key={filter_key}")
    if filter_value is not None:
        params.append(f"filter_value={filter_value}")
    qs = "&".join(params)
    url = f"{BASE}/events?{qs}"
    with urllib.request.urlopen(url, timeout=15) as r:
        data = json.loads(r.read().decode())
    return data.get("data", []) if isinstance(data, dict) else data


def get_stats() -> dict:
    try:
        with urllib.request.urlopen(f"{INDB_URL}/health", timeout=10) as r:
            health = json.loads(r.read().decode())
    except Exception:
        health = {}
    try:
        ev = query(limit=100)
        return {"status": "ok", "health": health, "events_count": len(ev)}
    except Exception as e:
        return {"error": str(e), "health": health}


def main():
    print("=== REST INDB Cycle (5 requests) ===\n")
    results = []

    # 1. Ingest epistemology
    print("1. INGEST: epistemology")
    try:
        r = ingest(
            ["epistemology", "philosophy", "knowledge", "truth", "belief"],
            "hermes://fetch/epistemology",
        )
        id1 = r.get("data", r).get("id", "?")
        print(f"   → Event ID: {id1}")
        results.append({"step": 1, "action": "ingest", "topic": "epistemology", "ok": True, "id": id1})
    except Exception as e:
        print(f"   → FAIL: {e}")
        results.append({"step": 1, "action": "ingest", "topic": "epistemology", "ok": False, "error": str(e)})
        sys.exit(1)

    # 2. Query epistemology
    print("2. QUERY: epistemology (filter_key=epistemology)")
    try:
        ev = query(filter_key="epistemology", filter_value="", limit=10)
        items = ev if isinstance(ev, list) else ev.get("events", [])
        print(f"   → Found {len(items)} event(s)")
        for i, e in enumerate(items[:3]):
            loc = e.get("location", "?")
            anchor = e.get("raw_data_anchor", [])[:5]
            print(f"      [{i+1}] {loc} | {anchor}")
        results.append({"step": 2, "action": "query", "topic": "epistemology", "ok": True, "count": len(items)})
    except Exception as e:
        print(f"   → FAIL: {e}")
        results.append({"step": 2, "action": "query", "topic": "epistemology", "ok": False, "error": str(e)})

    # 3. Ingest collective-memory
    print("3. INGEST: collective-memory")
    try:
        r = ingest(
            ["collective", "memory", "shared", "culture", "narrative"],
            "hermes://fetch/collective-memory",
        )
        id2 = r.get("data", r).get("id", "?")
        print(f"   → Event ID: {id2}")
        results.append({"step": 3, "action": "ingest", "topic": "collective-memory", "ok": True, "id": id2})
    except Exception as e:
        print(f"   → FAIL: {e}")
        results.append({"step": 3, "action": "ingest", "topic": "collective-memory", "ok": False, "error": str(e)})

    # 4. Query memory
    print("4. QUERY: memory (filter_key=memory)")
    try:
        ev = query(filter_key="memory", filter_value="", limit=10)
        items = ev if isinstance(ev, list) else ev.get("events", [])
        print(f"   → Found {len(items)} event(s)")
        for i, e in enumerate(items[:3]):
            loc = e.get("location", "?")
            anchor = e.get("raw_data_anchor", [])[:5]
            print(f"      [{i+1}] {loc} | {anchor}")
        results.append({"step": 4, "action": "query", "topic": "memory", "ok": True, "count": len(items)})
    except Exception as e:
        print(f"   → FAIL: {e}")
        results.append({"step": 4, "action": "query", "topic": "memory", "ok": False, "error": str(e)})

    # 5. Stats
    print("5. STATS")
    try:
        st = get_stats()
        print(f"   → {json.dumps(st, indent=2)[:300]}...")
        results.append({"step": 5, "action": "stats", "ok": True, "data": st})
    except Exception as e:
        print(f"   → FAIL: {e}")
        results.append({"step": 5, "action": "stats", "ok": False, "error": str(e)})

    # Summary
    ok_count = sum(1 for r in results if r.get("ok"))
    print(f"\n=== Done: {ok_count}/5 OK ===")
    out = Path(__file__).resolve().parent.parent / "reports" / "REST_CYCLE_RESULTS.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
