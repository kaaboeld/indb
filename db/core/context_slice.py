"""
ContextSlice — horizontal what-if without LLM.

From seed + abstract modifier: extract factors, rescore resonance cloud,
optional Prism pass with synthetic observer overlay.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from core.constants import SLICE_FACTOR_MIN_LEN, SLICE_SHIFT_MAX
from core.echo import ResonanceEngine, ResonanceResult
from core.prism import ObserverContext, PrismEngine, PrismResult


class SliceEdge(BaseModel):
    event_id: str
    base_score: float
    shifted_score: float
    delta: float
    matched_factors: List[str] = Field(default_factory=list)


class ContextSliceResult(BaseModel):
    seed_id: str
    what_if: str
    factors: List[str]
    edges: List[SliceEdge]
    prism: Optional[PrismResult] = None
    logic: str
    graph: Optional[Dict[str, Any]] = None


def extract_factors(what_if: str) -> List[str]:
    """Abstract modifier → token factors (no fixed persona catalog)."""
    text = what_if.lower().strip()
    text = re.sub(r"^what\s+if\s+", "", text)
    words = re.findall(r"[a-z0-9]+", text)
    seen: set[str] = set()
    factors: List[str] = []
    for w in words:
        if len(w) < SLICE_FACTOR_MIN_LEN or w in seen:
            continue
        seen.add(w)
        factors.append(w)
    return factors


def _observer_overlay(base: Optional[ObserverContext], factors: List[str]) -> ObserverContext:
    """Merge hypothetical factors into observer token weights (relational shift)."""
    weights: Dict[str, float] = {}
    vocabulary: Dict[str, List[str]] = {}
    harmonic: Dict[str, float] = {}
    if base:
        weights = dict(base.token_weights)
        vocabulary = {k: list(v) for k, v in base.vocabulary.items()}
        harmonic = dict(base.harmonic_weights)
    boost = min(SLICE_SHIFT_MAX, 0.15 * max(1, len(factors)))
    for f in factors:
        weights[f] = weights.get(f, 0.0) + boost
    vocabulary["hypothetical"] = list(factors)
    return ObserverContext(
        token_weights=weights,
        vocabulary=vocabulary,
        harmonic_weights=harmonic,
    )


def apply_horizontal_shift(
    cloud: List[ResonanceResult],
    factors: List[str],
    get_event,
) -> List[SliceEdge]:
    if not factors:
        return [
            SliceEdge(
                event_id=r.event_id,
                base_score=r.score,
                shifted_score=r.score,
                delta=0.0,
                matched_factors=[],
            )
            for r in cloud
        ]
    factor_set = set(factors)
    edges: List[SliceEdge] = []
    for res in cloud:
        event = get_event(res.event_id)
        if not event:
            continue
        event_tokens = set()
        for t in event.raw_data_anchor:
            tl = t.lower()
            event_tokens.add(tl)
            if ":" in tl:
                event_tokens.add(tl.split(":", 1)[1])
        matched = sorted(factor_set & event_tokens)
        overlap_ratio = len(matched) / len(factor_set)
        delta = min(SLICE_SHIFT_MAX, overlap_ratio * SLICE_SHIFT_MAX)
        shifted = min(1.0, res.score + delta * (1.0 - res.score))
        edges.append(
            SliceEdge(
                event_id=res.event_id,
                base_score=round(res.score, 4),
                shifted_score=round(shifted, 4),
                delta=round(shifted - res.score, 4),
                matched_factors=matched,
            )
        )
    edges.sort(key=lambda e: e.shifted_score, reverse=True)
    return edges


def describe_logic(factors: List[str], edges: List[SliceEdge], limit: int = 5) -> str:
    if not factors:
        return "No hypothetical factors extracted; scores unchanged."
    top = edges[:limit]
    if not top:
        return "No resonance edges to shift."
    parts = [
        f"Hypothetical factors: {', '.join(factors)}.",
        "Horizontal rescoring from seed (brick) across linked events:",
    ]
    for e in top:
        if e.matched_factors:
            parts.append(
                f"  {e.event_id[:8]}… base={e.base_score} → shifted={e.shifted_score} "
                f"(matched: {', '.join(e.matched_factors)})"
            )
        else:
            parts.append(
                f"  {e.event_id[:8]}… base={e.base_score} → shifted={e.shifted_score} (no factor overlap)"
            )
    return "\n".join(parts)


class ContextSliceEngine:
    def __init__(self, indb_instance) -> None:
        self.indb = indb_instance

    def _db(self):
        return getattr(self.indb, "db", self.indb)

    def _get_event(self, event_id: str):
        if hasattr(self.indb, "get_event"):
            return self.indb.get_event(event_id)
        db = self._db()
        for event in db.iter_events():
            if event.id == event_id:
                return event
        return None

    async def slice(
        self,
        seed_id: str,
        what_if: str,
        radius: float = 0.3,
        limit: int = 20,
        observer: Optional[ObserverContext] = None,
        query: Optional[str] = None,
    ) -> ContextSliceResult:
        seed = self._get_event(seed_id)
        if not seed and query:
            seed = self._resolve_seed_from_query(query)
            if seed:
                seed_id = seed.id
        if not seed:
            raise ValueError("Seed event not found")

        factors = extract_factors(what_if)
        echo = ResonanceEngine(self.indb)
        cloud = await echo.resonate(seed_event_id=seed_id, radius=radius, limit=limit)

        edges = apply_horizontal_shift(cloud, factors, self._get_event)
        logic = describe_logic(factors, edges)

        prism_result: Optional[PrismResult] = None
        if cloud:
            overlay = _observer_overlay(observer, factors)
            prism = PrismEngine(self.indb)
            prism_result = prism.synthesize(
                query=query or seed_id,
                identity_key=None,
                resonance_cloud=cloud,
                observer=overlay,
            )

        db = self._db()
        horizontal_meta = {}
        if hasattr(db, "resonance_graph") and db.resonance_graph is not None:
            horizontal_meta["resonance_graph"] = db.resonance_graph.stats()
        if hasattr(db, "causal_index") and db.causal_index is not None:
            horizontal_meta["causal_index"] = db.causal_index.stats()

        return ContextSliceResult(
            seed_id=seed_id,
            what_if=what_if,
            factors=factors,
            edges=edges,
            prism=prism_result,
            logic=logic,
            graph=horizontal_meta or None,
        )

    def _resolve_seed_from_query(self, query: str):
        db = self._db()
        query_lower = query.lower()
        query_tokens = set(query_lower.split())
        best_score = 0.0
        best_event = None
        for event in db.iter_events():
            event_tokens = set(t.lower() for t in event.raw_data_anchor)
            overlap = len(query_tokens & event_tokens)
            loc_match = any(qt in (event.location or "").lower() for qt in query_tokens)
            score = float(overlap) + (0.5 if loc_match else 0.0)
            if score > best_score:
                best_score, best_event = score, event
        return best_event
