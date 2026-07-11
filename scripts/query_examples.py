#!/usr/bin/env python3
"""Run sample queries against live data in the configured INDB API."""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List

import httpx

BASE_URL = os.environ.get("INDB_API_URL", "https://api.indb.tech").rstrip("/")
TIMEOUT = float(os.environ.get("INDB_HTTP_TIMEOUT", "30"))


def _client() -> httpx.Client:
    return httpx.Client(base_url=BASE_URL, timeout=TIMEOUT, follow_redirects=True)


def _unwrap(payload: Dict[str, Any]) -> Any:
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


def top_locations(client: httpx.Client, limit: int = 5) -> List[str]:
    response = client.get("/api/v2/analytics/overview")
    response.raise_for_status()
    overview = _unwrap(response.json())
    top = overview.get("database", {}).get("top_locations", {})
    return list(top.keys())[:limit]


def run_search(client: httpx.Client, query: str, limit: int = 5) -> None:
    print(f"\n🔍 Search: {query!r}")
    response = client.get("/api/v2/search", params={"q": query, "limit": limit})
    response.raise_for_status()
    events = _unwrap(response.json())
    if not isinstance(events, list):
        events = []
    print(f"   ✅ {len(events)} results")
    for index, event in enumerate(events[:5], start=1):
        tokens = event.get("raw_data_anchor") or event.get("tokens")
        location = event.get("location", "unknown")
        print(f"      {index}. [{location}] -> {tokens}")


def run_location_filter(client: httpx.Client, location: str, limit: int = 5) -> None:
    print(f"\n🗂️  Location: {location}")
    response = client.get(
        "/api/v2/events",
        params={"filter_key": "location", "filter_value": location, "limit": limit},
    )
    response.raise_for_status()
    events = _unwrap(response.json())
    if not isinstance(events, list):
        events = []
    print(f"   ✅ {len(events)} events")
    for index, event in enumerate(events[:3], start=1):
        tokens = event.get("raw_data_anchor") or event.get("tokens")
        print(f"      {index}. {tokens}")


def run_interpret(client: httpx.Client, location: str, limit: int = 5) -> None:
    payload = {"context": {"mood": "Neutral", "location": location}, "limit": limit}
    print(f"\n🧠 Interpret @ {location}")
    print(f"   Payload: {json.dumps(payload)}")
    response = client.post("/api/v2/interpret", json=payload)
    if response.status_code >= 400:
        print(f"   ❌ HTTP {response.status_code}: {response.text[:160]}")
        return
    data = _unwrap(response.json())
    events = data.get("events", []) if isinstance(data, dict) else []
    print(f"   ✅ {len(events)} results")
    for index, event in enumerate(events[:3], start=1):
        tokens = event.get("raw_data_anchor") or event.get("tokens")
        print(f"      {index}. {tokens}")


def main() -> int:
    print("=" * 60)
    print("INDB Query Examples (live data)")
    print(f"API: {BASE_URL}")
    print("=" * 60)

    try:
        with _client() as client:
            health = client.get("/health")
            health.raise_for_status()
            print(f"Health: {health.json().get('status', 'unknown')}")

            locations = top_locations(client)
            if not locations:
                print("No locations in database.")
                return 0

            for location in locations[:3]:
                run_location_filter(client, location, limit=5)

            for location in locations[:2]:
                token = location.rsplit("/", 1)[-1].lower()
                if token:
                    run_search(client, token, limit=5)

            for location in locations[:2]:
                run_interpret(client, location, limit=5)
    except httpx.ConnectError:
        print(
            f"❌ Cannot connect to {BASE_URL}. Set INDB_API_URL.",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:
        print(f"❌ Error: {exc}", file=sys.stderr)
        return 1

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
