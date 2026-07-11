#!/usr/bin/env python3
"""Run interpret/lens sample queries against the configured INDB API."""

from __future__ import annotations

import os
import sys
from collections import Counter
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


def fetch_events(client: httpx.Client, limit: int = 200) -> List[Dict[str, Any]]:
    response = client.get("/api/v2/events", params={"limit": limit})
    response.raise_for_status()
    data = _unwrap(response.json())
    return data if isinstance(data, list) else []


def run_interpret(client: httpx.Client, desc: str, payload: Dict[str, Any]) -> None:
    print(f"\n--- INTERPRET: {desc} ---")
    try:
        response = client.post("/api/v2/interpret", json=payload)
        response.raise_for_status()
        data = _unwrap(response.json())
        events = data.get("events", []) if isinstance(data, dict) else []
        print(f"Events found: {len(events)}")
        for event in events[:3]:
            anchor = event.get("raw_data_anchor", [])
            loc = event.get("original_location") or event.get("location", "unknown")
            print(f"  - {anchor} @ {loc}")
    except Exception as exc:
        print(f"Error: {exc}")


def run_lens(client: httpx.Client, desc: str, payload: Dict[str, Any]) -> None:
    print(f"\n--- LENS: {desc} ---")
    try:
        response = client.post("/api/v2/lens/query", json=payload)
        response.raise_for_status()
        data = _unwrap(response.json())
        if not isinstance(data, dict):
            print(f"No data: {data}")
            return
        meta = data.get("metadata", {})
        print(
            "Lens count: "
            f"{meta.get('lens_count')} "
            f"(H1: {meta.get('h1_count')}, H2: {meta.get('h2_count')})"
        )
        for event in data.get("lens_view", [])[:3]:
            anchor = event.get("raw_data_anchor", [])
            loc = event.get("location", "unknown")
            print(f"  - {anchor} @ {loc}")
    except Exception as exc:
        print(f"Error: {exc}")


def main() -> int:
    print(f"INDB API: {BASE_URL}")
    try:
        with _client() as client:
            health = client.get("/health")
            health.raise_for_status()
            print(f"Health: {health.json().get('status', 'unknown')}")

            events = fetch_events(client, limit=200)
            print(f"\n--- Source overview ({len(events)} events sampled) ---")
            locations = Counter(str(e.get("location", "unknown")) for e in events)
            for location, count in locations.most_common(10):
                print(f"  {count:4d}  {location}")

            if events:
                print("\n--- First 3 events ---")
                for event in events[:3]:
                    loc = event.get("location", "unknown")
                    tokens = event.get("raw_data_anchor", [])
                    preview = tokens[0] if tokens else "—"
                    print(f"  - {preview} @ {loc}")

            run_interpret(
                client,
                "Neutral scan",
                {"limit": 50, "context": {"mood": "Neutral"}},
            )
            run_lens(
                client,
                "Mixed view",
                {
                    "context_a": "all",
                    "context_b": "all",
                    "ratio": [0.5, 0.5],
                    "limit": 5,
                },
            )
    except httpx.ConnectError:
        print(
            f"Error: cannot connect to {BASE_URL}. "
            "Start INDB or set INDB_API_URL (e.g. https://api.indb.tech).",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
