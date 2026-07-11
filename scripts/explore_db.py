#!/usr/bin/env python3
"""Explore live INDB data via the configured API."""

from __future__ import annotations

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


def fmt_events(events: List[Dict[str, Any]]) -> None:
    for event in events:
        loc = event.get("location", "?")
        tags = ", ".join(event.get("raw_data_anchor", [])[:8])
        print(f"  [{loc}]  {tags}")


def analytics(client: httpx.Client) -> Dict[str, Any]:
    print(f"\n{'─' * 65}")
    print("ANALYTICS OVERVIEW")
    response = client.get("/api/v2/analytics/overview")
    response.raise_for_status()
    overview = _unwrap(response.json())
    db = overview.get("database", {})
    fusion = overview.get("fusion", {})
    health = overview.get("system_health", {})
    print(f"  Total events     : {db.get('total_events', '?')}")
    print(f"  Fusion rate      : {fusion.get('fusion_rate', '?')}%")
    print(f"  Unique locations : {db.get('unique_locations', '?')}")
    print(f"  Health score     : {overview.get('health_score', '?')}")
    print(f"  Memory RSS       : {health.get('memory_rss_mb', '?')} MB")
    top = db.get("top_locations", {})
    if top:
        print("\n  Top locations:")
        for location, count in sorted(top.items(), key=lambda item: -item[1]):
            print(f"    {count:5}  {location}")
    return overview


def fusion_stats(client: httpx.Client) -> None:
    print(f"\n{'─' * 65}")
    print("FUSION STATS")
    response = client.get("/api/v2/fusion/stats")
    response.raise_for_status()
    data = _unwrap(response.json())
    if isinstance(data, dict):
        for key, value in data.items():
            print(f"  {key:30s}: {value}")


def search(client: httpx.Client, query: str, limit: int = 5) -> None:
    print(f"\n{'─' * 65}")
    print(f"SEARCH: {query!r}")
    response = client.get("/api/v2/search", params={"q": query, "limit": limit})
    response.raise_for_status()
    events = _unwrap(response.json())
    if not isinstance(events, list):
        events = []
    print(f"  -> {len(events)} results")
    fmt_events(events)


def events_by_location(client: httpx.Client, location: str, limit: int = 5) -> None:
    print(f"\n{'─' * 65}")
    print(f"EVENTS @ {location}")
    response = client.get(
        "/api/v2/events",
        params={"filter_key": "location", "filter_value": location, "limit": limit},
    )
    response.raise_for_status()
    events = _unwrap(response.json())
    if not isinstance(events, list):
        events = []
    print(f"  -> {len(events)} results")
    fmt_events(events[:limit])


def main() -> int:
    print("=" * 65)
    print("INDB DATA EXPLORATION")
    print(f"API: {BASE_URL}")
    print("=" * 65)

    try:
        with _client() as client:
            health = client.get("/health")
            health.raise_for_status()
            print(f"Health: {health.json().get('status', 'unknown')}")

            overview = analytics(client)
            fusion_stats(client)

            top_locations = overview.get("database", {}).get("top_locations", {})
            for location in list(top_locations.keys())[:5]:
                events_by_location(client, location, limit=4)

            for location in list(top_locations.keys())[:3]:
                token = location.rsplit("/", 1)[-1].lower()
                if token:
                    search(client, token, limit=4)
    except httpx.ConnectError:
        print(f"Cannot connect to {BASE_URL}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"\n{'=' * 65}")
    print("DONE")
    print(f"{'=' * 65}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
