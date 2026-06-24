#!/usr/bin/env python3
"""
Abstract queries via Hermes: by location, context, substance.

Hermes calls mcp_indb_query_events with different filters.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

WORKFLOW_DIR = Path(__file__).resolve().parent
REPORT_DIR = WORKFLOW_DIR.parent / "reports"
HERMES_TIMEOUT = 90

QUERIES = [
    {
        "id": "location_wikipedia",
        "type": "location",
        "prompt": "Use mcp_indb_query_events with filter_key=location and filter_value=wikipedia. List what INDB has from Wikipedia sources. Summarize in 2-3 sentences.",
    },
    {
        "id": "location_arxiv",
        "type": "location",
        "prompt": "Use mcp_indb_query_events with filter_key=location and filter_value=arxiv. What events from arXiv are in INDB?",
    },
    {
        "id": "location_hermes",
        "type": "location",
        "prompt": "Use mcp_indb_query_events with filter_key=location and filter_value=hermes. Show Hermes-sourced events.",
    },
    {
        "id": "substance_epistemology",
        "type": "substance",
        "prompt": "Use mcp_indb_query_events with filter_key=epistemology and filter_value empty. Find events about epistemology. Summarize key concepts.",
    },
    {
        "id": "substance_memory",
        "type": "substance",
        "prompt": "Use mcp_indb_query_events with filter_key=memory and filter_value empty. What does INDB know about memory?",
    },
    {
        "id": "substance_paradox",
        "type": "substance",
        "prompt": "Query INDB for events about paradox. Use filter_key=paradox. Summarize.",
    },
    {
        "id": "context_truth",
        "type": "context",
        "prompt": "Find events related to truth and knowledge in INDB. Use query_events. What patterns do you see?",
    },
    {
        "id": "stats",
        "type": "stats",
        "prompt": "Use mcp_indb_get_stats. Report total_events, fusion rate, and any other metrics.",
    },
]


def run_hermes_query(prompt: str) -> Dict[str, Any]:
    """Run Hermes with query prompt."""
    start = time.time()
    try:
        result = subprocess.run(
            ["hermes", "chat", "-Q", "-q", prompt],
            capture_output=True,
            text=True,
            timeout=HERMES_TIMEOUT,
        )
        elapsed = time.time() - start
        return {
            "success": result.returncode == 0,
            "elapsed_sec": round(elapsed, 1),
            "stdout": (result.stdout or "")[:2000],
            "stderr": (result.stderr or "")[:500],
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for q in QUERIES:
        print(f"  Query: {q['id']} ({q['type']})")
        r = run_hermes_query(q["prompt"])
        r["query_id"] = q["id"]
        r["query_type"] = q["type"]
        results.append(r)
        print(f"    → {'OK' if r.get('success') else 'FAIL'}")
        time.sleep(2)

    out = REPORT_DIR / "ABSTRACT_QUERIES_RESULTS.json"
    with open(out, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
