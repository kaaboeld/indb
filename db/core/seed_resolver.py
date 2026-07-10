"""
Resolve a resonance seed (brick) from any base query result + params.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class SeedResolution:
    seed_id: Optional[str] = None
    query: Optional[str] = None
    source: str = "unknown"

    @property
    def resolved(self) -> bool:
        return bool(self.seed_id or self.query)


def resolve_seed(
    base_query_type: str,
    base_params: Dict[str, Any],
    base_result: Any,
) -> SeedResolution:
    """
    Map base query output → seed_id or text query for ContextSlice / Echo.
    """
    if not isinstance(base_result, dict):
        base_result = {}

    seed_id = base_params.get("seed_id")
    query = base_params.get("query") or base_params.get("q")

    if base_query_type == "echo":
        center = base_result.get("center")
        if center:
            return SeedResolution(seed_id=center, query=query, source="echo.center")
        if seed_id:
            return SeedResolution(seed_id=seed_id, query=query, source="echo.params")

    if base_query_type == "search":
        results = base_result.get("results") or []
        if results:
            top = results[0]
            eid = top.get("id") if isinstance(top, dict) else None
            if eid:
                return SeedResolution(
                    seed_id=eid,
                    query=query or base_result.get("query"),
                    source="search.top_hit",
                )

    if base_query_type == "prism":
        sid = base_result.get("seed_id")
        if sid:
            return SeedResolution(seed_id=sid, query=query, source="prism.seed_id")
        ev = base_result.get("event")
        if isinstance(ev, dict) and ev.get("id"):
            return SeedResolution(seed_id=ev["id"], query=query, source="prism.event")
        if query:
            return SeedResolution(query=query, source="prism.query")

    if base_query_type == "deduction":
        chain = base_result.get("chain") or []
        for step in chain:
            if isinstance(step, dict) and step.get("event_id"):
                return SeedResolution(
                    seed_id=step["event_id"],
                    query=query,
                    source="deduction.chain",
                )
        seeds = base_params.get("seed_event_ids") or []
        if seeds:
            return SeedResolution(seed_id=seeds[0], query=query, source="deduction.params")
        if query:
            return SeedResolution(query=query, source="deduction.query")

    if base_query_type == "interpret":
        events = base_result.get("events") or []
        best_id, best_act = _best_interpret_event_id(events)
        if best_id:
            return SeedResolution(seed_id=best_id, query=query, source="interpret.activation")
        if events:
            first = events[0]
            if isinstance(first, dict) and first.get("id"):
                return SeedResolution(seed_id=first["id"], query=query, source="interpret.first")

    if seed_id:
        return SeedResolution(seed_id=seed_id, query=query, source="params.seed_id")
    if query:
        return SeedResolution(query=query, source="params.query")
    return SeedResolution(source="unresolved")


def _best_interpret_event_id(events: list) -> tuple[Optional[str], float]:
    best_id: Optional[str] = None
    best_act = -1.0
    for ev in events:
        if not isinstance(ev, dict):
            continue
        eid = ev.get("id")
        if not eid:
            continue
        act = ev.get("activation_score", ev.get("activation", 0.0))
        try:
            act_f = float(act)
        except (TypeError, ValueError):
            act_f = 0.0
        if act_f > best_act:
            best_act = act_f
            best_id = eid
    return best_id, best_act
