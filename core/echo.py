"""
Echo (Resonance) Engine
"Lens focuses (Input). Echo radiates (Output)."

Calculates harmonic resonance between events based on:
1. Token Overlap (Jaccard)
2. Emotional Proximity (Vector/String match)
3. Temporal/Cyclic Resonance (Day of Year)
"""

import time
import logging
from typing import List, Dict, Optional, Set
from pydantic import BaseModel

logger = logging.getLogger("indb.echo")

from core.event import Event
from core.constants import ECHO_WEIGHT_TOKEN, ECHO_WEIGHT_EMOTION, ECHO_WEIGHT_META

class HarmonicWeights(BaseModel):
    token: float = ECHO_WEIGHT_TOKEN
    emotion: float = ECHO_WEIGHT_EMOTION
    meta: float = ECHO_WEIGHT_META

class ResonanceResult(BaseModel):
    event_id: str
    score: float
    harmonic_type: str      # 'direct', 'emotional', 'cyclic', 'mixed'
    reason: str             # "Shared tokens: [a, b]"

class ResonanceEngine:
    def __init__(self, indb_instance=None):
        self.indb = indb_instance
        self.weights = HarmonicWeights()

    def set_weights(self, w: HarmonicWeights):
        self.weights = w

    def _db(self):
        return getattr(self.indb, "db", self.indb)

    def _resolve_event(self, event_id: str) -> Optional[Event]:
        if hasattr(self.indb, "get_event"):
            return self.indb.get_event(event_id)
        db = self._db()
        if hasattr(db, "iter_events"):
            for event in db.iter_events():
                if event.id == event_id:
                    return event
        return None

    def calculate_resonance(self, seed: Event, target: Event) -> float:
        """
        R(A, B) = (Wt * T) + (We * E) + (Wm * M)
        Returns score 0.0 to 1.0
        """
        score_t = 0.0
        tokens_a = set(seed.raw_data_anchor)
        tokens_b = set(target.raw_data_anchor)

        if tokens_a and tokens_b:
            intersection = len(tokens_a.intersection(tokens_b))
            union = len(tokens_a.union(tokens_b))
            jaccard = intersection / union if union > 0 else 0.0
            if intersection > 0:
                partial_bonus = min(0.3, intersection * 0.1)
                score_t = jaccard + partial_bonus
            else:
                score_t = 0.0

        score_e = 0.0
        mood_a = seed.temporal_metadata.get("mood", "Neutral")
        mood_b = target.temporal_metadata.get("mood", "Neutral")
        if mood_a == mood_b and mood_a != "Neutral":
            score_e = 1.0
        else:
            score_e = 0.0

        score_m = 0.0
        if seed.location == target.location:
            score_m += 0.7

        struct_a = time.gmtime(seed.timestamp)
        struct_b = time.gmtime(target.timestamp)
        if struct_a.tm_mon == struct_b.tm_mon:
            score_m += 0.2
            if struct_a.tm_mday == struct_b.tm_mday:
                score_m += 0.1

        total_score = (
            (self.weights.token * score_t)
            + (self.weights.emotion * score_e)
            + (self.weights.meta * score_m)
        )
        return min(1.0, total_score)

    def _collect_candidate_ids(self, seed: Event, radius: float, limit: int) -> tuple[Set[str], str]:
        from core.horizontal_pool import collect_candidate_ids
        return collect_candidate_ids(self.indb, seed, radius, limit, self._resolve_event)

    async def resonate(self, seed_event_id: str, radius: float = 0.3, limit: int = 20) -> List[ResonanceResult]:
        """
        Emits a wave from seed_event to find resonating memories.
        Uses persisted graph + inverted index when available; falls back to full scan.
        """
        if not self.indb:
            return []

        seed = self._resolve_event(seed_event_id)
        if not seed:
            return []

        results: List[ResonanceResult] = []
        candidate_ids, scan_mode = self._collect_candidate_ids(seed, radius, limit)

        if candidate_ids:
            all_events = []
            for eid in candidate_ids:
                ev = self._resolve_event(eid)
                if ev and ev.id != seed_event_id:
                    all_events.append(ev)
        else:
            all_events = self.indb.get_all_events()
            scan_mode = "full"

        logger.debug(
            "Echo: %s scan of %d events for seed=%s (radius=%.2f)",
            scan_mode, len(all_events), seed_event_id[:8], radius,
        )

        scores_checked = 0
        for event in all_events:
            if event.id == seed_event_id:
                continue
            score = self.calculate_resonance(seed, event)
            scores_checked += 1
            if score >= radius:
                h_type = "strong" if score > 0.8 else "mixed"
                reason = f"Resonance Score: {score:.2f}" if score > 0.1 else ""
                results.append(ResonanceResult(
                    event_id=event.id,
                    score=score,
                    harmonic_type=h_type,
                    reason=reason,
                ))

        logger.debug(
            "Echo: found %d resonating events (checked %d)",
            len(results), scores_checked,
        )

        results.sort(key=lambda x: x.score, reverse=True)
        results = results[:limit]

        from core.memory_touch import touch_resonance, touch_resonance_events

        touch_resonance(seed)
        touched = [seed]
        for r in results:
            ev = self._resolve_event(r.event_id)
            if ev:
                touched.append(ev)
        touch_resonance_events(self.indb, touched)

        db = self._db()
        graph = getattr(db, "resonance_graph", None)
        if graph is not None and results:
            graph.record_wave(seed_event_id, results)
            graph.persist_if_dirty()

        return results
