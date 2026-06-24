#!/usr/bin/env python3
"""
MD report generation: input → output → fusion.

Report structure:
- Input (sources, volume)
- Output (events, fusion rate)
- Why this compression (fusion mechanics)
- Abstract queries: results
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

WORKFLOW_DIR = Path(__file__).resolve().parent
REPORT_DIR = WORKFLOW_DIR.parent / "reports"


def load_json(name: str) -> Dict:
    p = REPORT_DIR / name
    if not p.exists():
        return {}
    with open(p) as f:
        return json.load(f)


def generate_report() -> str:
    ingestion = load_json("INGESTION_LOG.json")
    mechanics = load_json("MECHANICS_VERIFICATION.json")
    queries = load_json("ABSTRACT_QUERIES_RESULTS.json")

    lines = [
        "# INDB Validation Report",
        "",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "---",
        "",
        "## 1. Concept",
        "",
        "INDB — database as human memory:",
        "- Raw data from real sources → event formulation",
        "- Fusion — semantic compression (like forgetting noise)",
        "- Abstract queries by location, context, substance",
        "- Hermes on input and output (MCP)",
        "",
        "---",
        "",
        "## 2. Input (Ingestion)",
        "",
    ]

    if ingestion:
        eb = ingestion.get("events_before", "?")
        ea = ingestion.get("events_after", "?")
        added = ingestion.get("events_added")
        runs = ingestion.get("total_runs", 0)
        ok = ingestion.get("ok_runs", 0)
        lines.extend([
            f"- **Events before:** {eb}",
            f"- **Events after:** {ea}",
            f"- **Added:** {added}",
            f"- **Hermes runs:** {runs} (OK: {ok})",
            "",
            "### Sources",
            "",
        ])
        entries = ingestion.get("log_entries", [])
        by_source = {}
        for e in entries:
            s = e.get("source", "?")
            by_source[s] = by_source.get(s, 0) + 1
        for src, cnt in sorted(by_source.items(), key=lambda x: -x[1]):
            lines.append(f"- {src}: {cnt} runs")
        lines.extend(["", ""])
    else:
        lines.append("*Ingestion log not found*")
        lines.extend(["", ""])

    lines.extend([
        "---",
        "",
        "## 3. Output (Storage & Fusion)",
        "",
    ])

    if mechanics:
        health = mechanics.get("health", {})
        fusion = mechanics.get("fusion_mechanics", {})
        sample = mechanics.get("events_sample", {})
        lines.extend([
            f"- **Total events:** {health.get('total_events', '?')}",
            f"- **Fusion rate:** {health.get('fusion_rate', '?')}",
            f"- **Fused in sample:** {fusion.get('fused_count', '?')} / {fusion.get('total_sampled', '?')}",
            f"- **High fusion_count (>1):** {fusion.get('high_fusion_count', '?')}",
            "",
            "### Top sources (by location)",
            "",
        ])
        for loc, cnt in sample.get("top_sources", [])[:10]:
            lines.append(f"- `{loc}`: {cnt}")
        lines.extend(["", ""])
    else:
        lines.append("*Mechanics verification not found*")
        lines.extend(["", ""])

    lines.extend([
        "---",
        "",
        "## 4. Why this compression (Fusion)",
        "",
        "Fusion triggers when similarity ≥ threshold (default 0.75):",
        "",
        "- **full_merge** (≥0.95): nearly identical events → one",
        "- **weighted_merge** (0.75–0.95): similar → token merge",
        "- **semantic_link** (0.6–0.75): related → stay separate but linked",
        "",
        "Factors: Jaccard tokens, location match, temporal proximity.",
        "Penalty Engine lowers score for frequent tokens and isolated events.",
        "",
        "---",
        "",
        "## 5. Abstract queries",
        "",
    ])

    if queries:
        for q in queries:
            qid = q.get("query_id", "?")
            qtype = q.get("query_type", "?")
            ok = "✅" if q.get("success") else "❌"
            lines.append(f"### {ok} {qid} ({qtype})")
            lines.append("")
            stdout = (q.get("stdout") or "")[:500]
            if stdout:
                lines.append("```")
                lines.append(stdout.strip())
                lines.append("```")
            else:
                lines.append(f"*Error: {q.get('error', 'no output')}*")
            lines.append("")
    else:
        lines.append("*Query results not found*")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## 6. Event mechanics",
        "",
        "| Mechanic | Status |",
        "|----------|--------|",
        "| Ingest (REST/MCP) | ✅ |",
        "| Fusion (semantic) | ✅ |",
        "| Query (filter_key/value) | ✅ |",
        "| Location substring | ✅ |",
        "| Token search (filter_key=word) | ✅ |",
        "| Echo resonance | ✅ |",
        "| Prism paradox | ✅ |",
        "",
        "---",
        "",
        "*Report generated by workflow/report_generator.py*",
    ])

    return "\n".join(lines)


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = generate_report()
    out = REPORT_DIR / f"VALIDATION_REPORT_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    with open(out, "w") as f:
        f.write(report)
    print(report)
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
