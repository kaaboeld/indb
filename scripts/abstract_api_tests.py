#!/usr/bin/env python3
"""
Abstract API Tests — conceptual queries across all INDB abstraction types.

Types (from docs/*):
- location: filter_key=location, filter_value
- raw/substance: filter_key=token, filter_value='' (search by raw_data_anchor)
- temporal: temporal_query in /interpret
- context: context.mood, context.goal in /interpret
- lens: context_a, context_b, ratio (recent/historical, high_frequency/simple)
- prism: synthesize with query, observer_context
- echo: resonate with seed_id
- advanced: /events/query with FilterCriteria (AND/OR, eq/contains/gt/lt/in)
- search: GET /search?q=
- analytics: temporal, tokens, database, insights
- fusion: top
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import urllib.request
import urllib.error

BASE = os.environ.get("INDB_API_URL", "http://localhost:8888")
API = f"{BASE}/api/v2"
REPORT_DIR = Path(__file__).resolve().parent.parent / "reports"


def req(method: str, path: str, body: dict | None = None, params: str = "") -> dict:
    url = f"{API}{path}"
    if params:
        url += ("&" if "?" in url else "?") + params
    data = json.dumps(body).encode() if body else None
    req_obj = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    with urllib.request.urlopen(req_obj, timeout=30) as r:
        return json.loads(r.read().decode())


def get(path: str, params: str = "") -> dict:
    url = f"{API}{path}"
    if params:
        url += ("&" if "?" in url else "?") + params
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode())


# ── Test Cases (by abstraction type) ─────────────────────────────────────────

TESTS = [
    # 1. Location
    {
        "id": "location_hermes",
        "type": "location",
        "desc": "Events by location (hermes)",
        "run": lambda: get("/events", "limit=10&filter_key=location&filter_value=hermes"),
        "check": lambda r: len(r.get("data", [])) >= 0 and "data" in r,
    },
    {
        "id": "location_wikipedia",
        "type": "location",
        "desc": "Events by location (wikipedia)",
        "run": lambda: get("/events", "limit=10&filter_key=location&filter_value=wikipedia"),
        "check": lambda r: "data" in r,
    },
    # 2. Raw / Substance (token search in raw_data_anchor)
    {
        "id": "substance_epistemology",
        "type": "raw",
        "desc": "Events by token epistemology",
        "run": lambda: get("/events", "limit=10&filter_key=epistemology&filter_value="),
        "check": lambda r: "data" in r,
    },
    {
        "id": "substance_memory",
        "type": "raw",
        "desc": "Events by token memory",
        "run": lambda: get("/events", "limit=10&filter_key=memory&filter_value="),
        "check": lambda r: "data" in r,
    },
    # 3. Search (semantic)
    {
        "id": "search_epistemology",
        "type": "search",
        "desc": "GET /search for epistemology",
        "run": lambda: get("/search", "q=epistemology&limit=5"),
        "check": lambda r: "data" in r and "meta" in r,
    },
    {
        "id": "search_memory",
        "type": "search",
        "desc": "GET /search for memory truth",
        "run": lambda: get("/search", "q=memory+truth&limit=5"),
        "check": lambda r: "data" in r,
    },
    # 4. Interpret (context + temporal)
    {
        "id": "interpret_context",
        "type": "context",
        "desc": "POST /interpret with context.mood",
        "run": lambda: req("POST", "/interpret", {"context": {"mood": "Neutral"}, "limit": 5}),
        "check": lambda r: "data" in r,
    },
    {
        "id": "interpret_temporal",
        "type": "temporal",
        "desc": "POST /interpret with temporal_query",
        "run": lambda: req("POST", "/interpret", {
            "context": {"mood": "Neutral"},
            "temporal_query": "last 24 hours",
            "limit": 5,
        }),
        "check": lambda r: "data" in r,
    },
    # 5. Lens (contextual blend)
    {
        "id": "lens_recent_historical",
        "type": "lens",
        "desc": "Lens: recent + historical 50/50",
        "run": lambda: req("POST", "/lens/query", {
            "context_a": "recent",
            "context_b": "historical",
            "ratio": [0.5, 0.5],
            "mode": "sharp",
            "limit": 5,
        }),
        "check": lambda r: "data" in r or "status" in r,
    },
    {
        "id": "lens_complexity",
        "type": "lens",
        "desc": "Lens: high_frequency + simple",
        "run": lambda: req("POST", "/lens/query", {
            "context_a": "high_frequency",
            "context_b": "simple",
            "ratio": [0.7, 0.3],
            "mode": "sharp",
            "limit": 5,
        }),
        "check": lambda r: "data" in r or "status" in r,
    },
    # 6. Prism (cognitive synthesis)
    {
        "id": "prism_synthesize",
        "type": "prism",
        "desc": "POST /prism/synthesize",
        "run": lambda: req("POST", "/prism/synthesize", {"query": "epistemology memory", "limit": 5}),
        "check": lambda r: "meaning" in r or "alternative_readings" in r or "perception_gap" in r,
    },
    # 7. Echo (resonance) — requires seed event_id
    {
        "id": "echo_resonate",
        "type": "echo",
        "desc": "POST /echo/resonate (seed from first event)",
        "run": lambda: _echo_resonate(),
        "check": lambda r: "center" in r or "ripples" in r or "detail" in str(r),
    },
    # 8. Advanced filter (AND/OR, eq/contains)
    {
        "id": "advanced_filter",
        "type": "advanced",
        "desc": "POST /events/query with FilterCriteria",
        "run": lambda: req("POST", "/events/query", {
            "operator": "AND",
            "criteria": [
                {"field": "location", "op": "contains", "value": "hermes"},
                {"field": "raw_data_anchor", "op": "contains", "value": "memory"},
            ],
        }),
        "check": lambda r: "data" in r,
    },
    # 9. Analytics
    {
        "id": "analytics_temporal",
        "type": "analytics",
        "desc": "GET /analytics/temporal",
        "run": lambda: get("/analytics/temporal"),
        "check": lambda r: "data" in r,
    },
    {
        "id": "analytics_tokens",
        "type": "analytics",
        "desc": "GET /analytics/tokens",
        "run": lambda: get("/analytics/tokens"),
        "check": lambda r: "data" in r,
    },
    {
        "id": "analytics_database",
        "type": "analytics",
        "desc": "GET /analytics/database",
        "run": lambda: get("/analytics/database"),
        "check": lambda r: "data" in r,
    },
    {
        "id": "analytics_insights",
        "type": "analytics",
        "desc": "GET /analytics/insights",
        "run": lambda: get("/analytics/insights"),
        "check": lambda r: "data" in r,
    },
    # 10. Fusion
    {
        "id": "fusion_top",
        "type": "fusion",
        "desc": "GET /fusion/top",
        "run": lambda: get("/fusion/top", "limit=5"),
        "check": lambda r: "data" in r or "status" in r,
    },
]


def _echo_resonate() -> dict:
    """Echo requires seed event_id — take first from /events."""
    events = get("/events", "limit=1")
    data = events.get("data", [])
    if not data:
        return {"detail": "No events for seed"}
    seed_id = data[0].get("id")
    return req("POST", "/echo/resonate", {"seed_id": seed_id, "radius": 0.3, "limit": 5})


def run_all() -> List[Dict[str, Any]]:
    results = []
    for t in TESTS:
        start = time.time()
        try:
            r = t["run"]()
            ok = t["check"](r)
            elapsed = round(time.time() - start, 2)
            results.append({
                "id": t["id"],
                "type": t["type"],
                "desc": t["desc"],
                "ok": ok,
                "elapsed_sec": elapsed,
                "sample": _sample(r),
            })
            print(f"  {t['id']} ({t['type']}): {'OK' if ok else 'FAIL'}")
        except Exception as e:
            results.append({
                "id": t["id"],
                "type": t["type"],
                "desc": t["desc"],
                "ok": False,
                "error": str(e),
            })
            print(f"  {t['id']} ({t['type']}): ERROR {e}")
    return results


def _truncate(val: Any, max_len: int = 120) -> Any:
    """Truncate long strings for report."""
    if isinstance(val, str) and len(val) > max_len:
        return val[:max_len] + "..."
    if isinstance(val, list) and len(val) > 5:
        return val[:5] + [f"... (+{len(val) - 5} more)"]
    return val


def _event_for_report(evt: dict, max_str: int = 120) -> dict:
    """Event for report — truncated fields."""
    out = {}
    for k, v in evt.items():
        if k in ("raw_data_anchor", "blind_payload") and isinstance(v, list):
            out[k] = v[:5] if len(v) <= 5 else v[:5] + [f"... (+{len(v) - 5})"]
        elif isinstance(v, str) and len(v) > max_str:
            out[k] = v[:max_str] + "..."
        elif isinstance(v, (int, float, bool, type(None))):
            out[k] = v
        else:
            out[k] = v
    return out


def _sample(r: dict, max_events: int = 5) -> Any:
    """Response sample: up to 5 events + metadata."""
    if "data" in r:
        d = r["data"]
        if isinstance(d, list) and d:
            events_sample = [_event_for_report(e) if isinstance(e, dict) else e for e in d[:max_events]]
            return {
                "count": len(d),
                "events_sample": events_sample,
            }
        if isinstance(d, dict):
            return {"data_keys": list(d.keys()), "data_sample": _event_for_report(d)}
    # prism, echo, etc.
    if "meaning" in r or "alternative_readings" in r:
        return {
            "meaning": str(r.get("meaning", ""))[:200],
            "alternative_readings": r.get("alternative_readings", [])[:3],
            "perception_gap": r.get("perception_gap"),
        }
    if "center" in r or "ripples" in r:
        return {k: _truncate(str(v), 150) for k, v in list(r.items())[:8]}
    return {k: _truncate(str(v), 100) for k, v in list(r.items())[:6]}


def _write_report(results: List[Dict[str, Any]], ok_count: int) -> None:
    """Write report with event samples (up to 5 per test)."""
    report_path = REPORT_DIR / "INTEGRATION_REPORT_2026-03.md"
    by_type: Dict[str, List[Dict]] = {}
    for r in results:
        t = r.get("type", "other")
        by_type.setdefault(t, []).append(r)

    lines = [
        "# INDB Integration Report — Abstract API Tests",
        "",
        f"**Date:** 2026-03-12  ",
        f"**Base URL:** {BASE}  ",
        f"**Result:** {ok_count}/{len(results)} OK",
        "",
        "### Summary",
        "",
        "| Type | OK | Errors |",
        "|-----|----|--------|",
    ]
    for ttype, items in sorted(by_type.items()):
        ok_n = sum(1 for r in items if r.get("ok"))
        err_n = len(items) - ok_n
        err_list = ", ".join(r["id"] for r in items if not r.get("ok")) if err_n else "—"
        lines.append(f"| {ttype} | {ok_n}/{len(items)} | {err_list} |")
    lines.extend(["", "---", "", "## Abstract API — tests with response samples (up to 5 events)", ""])

    for ttype, items in sorted(by_type.items()):
        lines.append(f"### {ttype}")
        lines.append("")
        for r in items:
            status = "OK" if r.get("ok") else ("ERROR" if r.get("error") else "FAIL")
            lines.append(f"#### {r['id']} — {status}")
            lines.append("")
            lines.append(f"- **Description:** {r.get('desc', '')}")
            if r.get("error"):
                lines.append(f"- **Error:** `{r['error']}`")
            sample = r.get("sample", {})
            events_sample = sample.get("events_sample")
            if events_sample:
                lines.append(f"- **Total events:** {sample.get('count', 0)}")
                lines.append("- **Samples (up to 5):**")
                for i, evt in enumerate(events_sample, 1):
                    lines.append("")
                    lines.append(f"  **Event {i}:**")
                    lines.append("  ```json")
                    lines.append(json.dumps(evt, ensure_ascii=False, indent=4))
                    lines.append("  ```")
            elif sample:
                lines.append("- **Response:**")
                lines.append("  ```json")
                lines.append(json.dumps(sample, ensure_ascii=False, indent=2))
                lines.append("  ```")
            lines.append("")
        lines.append("")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  Report: {report_path}")


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"=== Abstract API Tests ===")
    print(f"  Base: {BASE}")
    print("")
    results = run_all()
    ok_count = sum(1 for r in results if r.get("ok"))
    print(f"\n  {ok_count}/{len(results)} OK")
    out = REPORT_DIR / "ABSTRACT_API_TESTS.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"base": BASE, "results": results}, f, indent=2, ensure_ascii=False)
    print(f"  Saved: {out}")
    _write_report(results, ok_count)
    return 0 if ok_count == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
