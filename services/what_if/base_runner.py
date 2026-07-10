"""
What-If base query runner — executes interpret/search/echo/prism/deduction internally.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from core.constants import INTERPRET_MOOD_DEFAULT
from core.echo import ResonanceEngine
from core.prism import PrismEngine
from core.deduction import DeductionEngine


def _calculate_relevance(event, query_tokens: set, query_lower: str, fuzzy: bool) -> Tuple[float, List[str]]:
    """Helper for search (mirrors routes/query.py)."""
    score = 0.0
    matches = []
    event_tokens = [t.lower() for t in event.raw_data_anchor]
    for token in event_tokens:
        token_parts = token.split(":", 1)
        token_val = token_parts[1] if len(token_parts) > 1 else token
        if fuzzy:
            for q_token in query_tokens:
                if q_token in token or token in q_token:
                    score += 2.0
                    matches.append(token)
        else:
            for q_token in query_tokens:
                if q_token == token or q_token == token_val:
                    score += 2.0
                    matches.append(token)
    if any(qt in event.location.lower() for qt in query_tokens):
        score += 1.0
        matches.append(f"location:{event.location}")
    if score == 0:
        return 0.0, []
    if any("era:ancient" in t for t in event_tokens) and "ancient" not in query_lower:
        score *= 0.7
    return max(0.0, score), matches


async def run_base_query(indb, base_query_type: str, base_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute base query and return result as dict for LLM summarization.
    Raises ValueError for unknown type or invalid params.
    """
    if base_query_type == "search":
        q = base_params.get("q", "")
        limit = base_params.get("limit", 100)
        fuzzy = base_params.get("fuzzy", False)
        query_lower = q.lower()
        query_tokens = set(query_lower.split())
        results = []
        for event in indb.iter_events():
            score, matches = _calculate_relevance(event, query_tokens, query_lower, fuzzy)
            if score > 0:
                results.append({
                    "id": event.id,
                    "location": event.location,
                    "tokens": event.raw_data_anchor[:10],
                    "relevance_score": round(score, 2),
                    "matches": list(set(matches))[:5],
                })
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return {"query": q, "results": results[:limit], "count": len(results)}

    if base_query_type == "interpret":
        context = base_params.get("context", {})
        temporal_query = base_params.get("temporal_query")
        mood = context.get("mood", INTERPRET_MOOD_DEFAULT)
        raw_events = list(indb.iter_events())
        if temporal_query:
            raw_events = indb.db.filter_by_temporal_query(raw_events, temporal_query)
        events = indb.db.scan("", "", context_mood=mood, events_to_scan=raw_events)
        data = [e if isinstance(e, dict) else e.to_dict() for e in events]
        return {"context_mood": mood, "events": data[:50], "count": len(data)}

    if base_query_type == "echo":
        seed_id = base_params.get("seed_id")
        radius = base_params.get("radius", 0.3)
        limit = base_params.get("limit", 20)
        if not seed_id:
            raise ValueError("echo requires seed_id")
        engine = ResonanceEngine(indb)
        ripples = await engine.resonate(seed_event_id=seed_id, radius=radius, limit=limit)
        return {
            "center": seed_id,
            "ripples": [
                {"event_id": r.event_id, "score": r.score, "harmonic_type": r.harmonic_type, "reason": r.reason}
                for r in ripples
            ],
        }

    if base_query_type == "prism":
        query = base_params.get("query")
        radius = base_params.get("radius", 0.3)
        limit = base_params.get("limit", 20)
        if not query:
            raise ValueError("prism requires query")
        echo_engine = ResonanceEngine(indb)
        prism_engine = PrismEngine(indb)
        seed_id = query
        seed = indb.get_event(seed_id)
        if not seed:
            query_lower = query.lower()
            query_tokens = set(query_lower.split())
            best_score, best_event = 0.0, None
            for event in indb.iter_events():
                event_tokens = set(t.lower() for t in event.raw_data_anchor)
                overlap = len(query_tokens & event_tokens)
                loc_match = any(qt in event.location.lower() for qt in query_tokens)
                score = float(overlap) + (0.5 if loc_match else 0.0)
                if score > best_score:
                    best_score, best_event = score, event
            if not best_event:
                raise ValueError("No matching event found for prism query")
            seed_id = best_event.id
        cloud = await echo_engine.resonate(seed_event_id=seed_id, radius=radius, limit=limit)
        if not cloud:
            raise ValueError("No resonance found for prism")
        result = prism_engine.synthesize(query=query, identity_key=None, resonance_cloud=cloud, observer=None)
        if not result:
            raise ValueError("Prism could not crystallize a result")
        return {
            "seed_id": seed_id,
            "event": result.event.model_dump() if hasattr(result.event, "model_dump") else result.event,
            "meaning": result.meaning.model_dump() if hasattr(result.meaning, "model_dump") else result.meaning,
            "alternative_readings": [
                m.model_dump() if hasattr(m, "model_dump") else m
                for m in result.alternative_readings
            ],
            "perception_gap": result.perception_gap,
            "is_paradoxical": result.is_paradoxical,
        }

    if base_query_type == "deduction":
        seed_event_ids = base_params.get("seed_event_ids")
        query = base_params.get("query")
        radius = base_params.get("radius", 0.35)
        limit = base_params.get("limit", 15)
        if not seed_event_ids and not query:
            raise ValueError("deduction requires query or seed_event_ids")
        engine = DeductionEngine(indb)
        result = await engine.deduce(
            seed_event_ids=seed_event_ids,
            query=query,
            radius=radius,
            limit=limit,
        )
        chain = [
            {"event_id": s.event_id, "reason": s.reason, "step_type": s.step_type}
            for s in result.chain
        ]
        seed_from_chain = chain[0]["event_id"] if chain else None
        return {
            "seed_id": seed_from_chain,
            "chain": chain,
            "conclusion": result.conclusion,
            "confidence": result.confidence,
            "reasoning": result.reasoning,
        }

    raise ValueError(f"Unknown base_query_type: {base_query_type}")
