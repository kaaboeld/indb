"""
Subwave Network — unified resonance broadcast from an anchor (seed).

All candidate nodes are scored against one frequency signature derived from the
anchor (and optional modifier). Nodes above threshold "lock in" — horizontal
response without re-scanning the full universe.

Conceptual parallel: one anchor (TARDIS/Earth) + subwave tuning → planets resonate
in phase and the structure coheres (materialized graph, not attention O(N²)).
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Set

from pydantic import BaseModel, Field

from core.constants import (
    SUBWAVE_LOCK_THRESHOLD,
    SUBWAVE_MAX_NODES,
    SUBWAVE_WEIGHT_FACTOR,
    SUBWAVE_WEIGHT_RESONANCE,
    SUBWAVE_WEIGHT_TOKEN,
)
from core.context_slice import extract_factors
from core.echo import ResonanceEngine, ResonanceResult
from core.event import Event
from core.horizontal_pool import collect_candidate_ids

logger = logging.getLogger("indb.subwave")


class ResonanceSignature(BaseModel):
    """Unified broadcast frequency — derived from anchor + optional modifier."""
    anchor_id: str
    tokens: List[str] = Field(default_factory=list)
    location: str = ""
    factors: List[str] = Field(default_factory=list)


class LockedNode(BaseModel):
    event_id: str
    lock_score: float
    resonance_score: float
    token_alignment: float
    factor_alignment: float
    location: str = ""


class SubwaveResult(BaseModel):
    anchor: ResonanceSignature
    locked_nodes: List[LockedNode]
    coherence: float
    scan_mode: str
    nodes_tuned: int
    nodes_locked: int


def _token_set(event: Event) -> Set[str]:
    out: Set[str] = set()
    for t in event.raw_data_anchor:
        tl = t.lower()
        out.add(tl)
        if ":" in tl:
            out.add(tl.split(":", 1)[1])
    return out


def _alignment(haystack: Set[str], needles: Set[str]) -> float:
    if not needles:
        return 0.0
    return len(haystack & needles) / len(needles)


class SubwaveEngine:
    """Broadcast one frequency from anchor; collect in-phase locked nodes."""

    def __init__(self, indb_instance) -> None:
        self.indb = indb_instance
        self.echo = ResonanceEngine(indb_instance)

    def _resolve_event(self, event_id: str) -> Optional[Event]:
        if hasattr(self.indb, "get_event"):
            return self.indb.get_event(event_id)
        db = getattr(self.indb, "db", self.indb)
        for event in db.iter_events():
            if event.id == event_id:
                return event
        return None

    def build_signature(self, seed: Event, modifier: Optional[str] = None) -> ResonanceSignature:
        factors = extract_factors(modifier) if modifier else []
        tokens = sorted(_token_set(seed))[:50]
        return ResonanceSignature(
            anchor_id=seed.id,
            tokens=tokens,
            location=(seed.location or "").strip(),
            factors=factors,
        )

    async def broadcast(
        self,
        seed_id: str,
        query: Optional[str] = None,
        modifier: Optional[str] = None,
        radius: float = 0.3,
        limit: int = SUBWAVE_MAX_NODES,
        lock_threshold: float = SUBWAVE_LOCK_THRESHOLD,
    ) -> SubwaveResult:
        seed = self._resolve_event(seed_id) if seed_id else None
        if not seed and query:
            seed = self._resolve_query(query)
            if seed:
                seed_id = seed.id
        if not seed:
            raise ValueError("Anchor event not found (provide seed_id or query)")

        signature = self.build_signature(seed, modifier)
        sig_tokens = set(signature.tokens) | set(signature.factors)
        factor_set = set(signature.factors)

        candidate_ids, scan_mode = collect_candidate_ids(
            self.indb, seed, radius, limit, self._resolve_event
        )

        if candidate_ids:
            events = [
                ev
                for eid in candidate_ids
                if (ev := self._resolve_event(eid)) and ev.id != seed.id
            ]
        else:
            events = [
                ev
                for ev in self.indb.get_all_events()
                if ev.id != seed.id
            ]
            scan_mode = "full"

        locked: List[LockedNode] = []
        for event in events:
            res_score = self.echo.calculate_resonance(seed, event)
            event_tokens = _token_set(event)
            token_align = _alignment(event_tokens, sig_tokens)
            factor_align = _alignment(event_tokens, factor_set) if factor_set else 0.0
            lock_score = min(
                1.0,
                SUBWAVE_WEIGHT_RESONANCE * res_score
                + SUBWAVE_WEIGHT_TOKEN * token_align
                + SUBWAVE_WEIGHT_FACTOR * factor_align,
            )
            if lock_score >= lock_threshold:
                locked.append(
                    LockedNode(
                        event_id=event.id,
                        lock_score=round(lock_score, 4),
                        resonance_score=round(res_score, 4),
                        token_alignment=round(token_align, 4),
                        factor_alignment=round(factor_align, 4),
                        location=event.location or "",
                    )
                )

        locked.sort(key=lambda n: n.lock_score, reverse=True)
        locked = locked[:limit]

        from core.memory_touch import touch_resonance, touch_resonance_events

        touch_resonance(seed)
        locked_events = [
            ev
            for n in locked
            if (ev := self._resolve_event(n.event_id))
        ]
        touch_resonance_events(self.indb, [seed, *locked_events])

        coherence = (
            sum(n.lock_score for n in locked) / len(locked) if locked else 0.0
        )

        db = getattr(self.indb, "db", self.indb)
        graph = getattr(db, "resonance_graph", None)
        if graph is not None and locked:
            ripples = [
                ResonanceResult(
                    event_id=n.event_id,
                    score=n.resonance_score,
                    harmonic_type="subwave",
                    reason=f"Subwave lock {n.lock_score:.2f}",
                )
                for n in locked
            ]
            graph.record_wave(seed_id, ripples)
            graph.persist_if_dirty()

        return SubwaveResult(
            anchor=signature,
            locked_nodes=locked,
            coherence=round(coherence, 4),
            scan_mode=scan_mode,
            nodes_tuned=len(events),
            nodes_locked=len(locked),
        )

    def _resolve_query(self, query: str) -> Optional[Event]:
        query_lower = query.lower()
        query_tokens = set(query_lower.split())
        best_score = 0.0
        best_event = None
        db = getattr(self.indb, "db", self.indb)
        for event in db.iter_events():
            event_tokens = set(t.lower() for t in event.raw_data_anchor)
            overlap = len(query_tokens & event_tokens)
            loc_match = any(qt in (event.location or "").lower() for qt in query_tokens)
            score = float(overlap) + (0.5 if loc_match else 0.0)
            if score > best_score:
                best_score, best_event = score, event
        return best_event
