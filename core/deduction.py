"""
Deduction Engine — Sherlock Holmes Thinking

"Given the facts, what can we infer?"

Chain inference from events:
- Temporal: A before B before C → sequence
- Spatial: A and B at same location → co-presence
- Token: shared tokens → thematic connection
- Causal heuristic: temporal proximity + overlap → likely chain

Returns: evidence chain, conclusion, confidence.
"""

import time
import logging
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel

from core.event import Event
from core.echo import ResonanceEngine, ResonanceResult

logger = logging.getLogger("indb.deduction")


class InferenceStep(BaseModel):
    """Single step in a deduction chain"""
    event_id: str
    reason: str           # "Temporal: preceded by X" / "Spatial: same location as Y" / "Token: shared [a,b]"
    step_type: str        # "temporal", "spatial", "token", "seed"
    confidence: float     # 0.0–1.0


class DeductionResult(BaseModel):
    """Result of deduction from evidence"""
    chain: List[InferenceStep]
    conclusion: str
    confidence: float
    evidence_count: int
    reasoning: str        # Human-readable trace


class DeductionEngine:
    """
    Deduction Engine — infers conclusions from event chains.

    Given seed events (or a query), expands the evidence cloud via Echo,
    orders by time, and builds inference chains.
    """

    def __init__(self, indb_instance=None):
        self.indb = indb_instance
        self.echo = ResonanceEngine(indb_instance) if indb_instance else None

    async def deduce(
        self,
        seed_event_ids: Optional[List[str]] = None,
        query: Optional[str] = None,
        radius: float = 0.35,
        limit: int = 15,
    ) -> DeductionResult:
        """
        Run deduction from seeds or a text query.

        If seed_event_ids: use these as starting evidence.
        If query: resolve to closest matching event(s), then expand.

        Returns chain of inferred events + synthesized conclusion.
        """
        if not self.indb or not self.echo:
            return DeductionResult(
                chain=[],
                conclusion="Deduction engine unavailable.",
                confidence=0.0,
                evidence_count=0,
                reasoning="INDB not initialized.",
            )

        # Step 1: Resolve seeds
        seeds: List[Event] = []
        if seed_event_ids:
            for eid in seed_event_ids[:5]:  # Max 5 seeds
                ev = self.indb.get_event(eid)
                if ev:
                    seeds.append(ev)
        if not seeds and query:
            seeds = self._resolve_query_to_events(query, limit=3)

        if not seeds:
            return DeductionResult(
                chain=[],
                conclusion="No evidence found.",
                confidence=0.0,
                evidence_count=0,
                reasoning="No seed events matched.",
            )

        # Step 2: Expand evidence cloud via Echo from each seed
        seen_ids: set = set()
        all_related: List[Tuple[Event, float, str]] = []  # (event, score, reason)

        for seed in seeds:
            seen_ids.add(seed.id)
            ripples = await self.echo.resonate(
                seed_event_id=seed.id,
                radius=radius,
                limit=limit,
            )
            for r in ripples:
                if r.event_id not in seen_ids:
                    ev = self.indb.get_event(r.event_id)
                    if ev:
                        all_related.append((ev, r.score, r.reason))
                        seen_ids.add(r.event_id)

        # Step 3: Add seeds to pool, sort by timestamp
        pool: List[Event] = list(seeds)
        for ev, _, _ in all_related:
            pool.append(ev)
        pool.sort(key=lambda e: e.timestamp)

        if len(pool) < 2:
            single = pool[0] if pool else None
            if single:
                conclusion = self._synthesize_single(single)
                return DeductionResult(
                    chain=[
                        InferenceStep(
                            event_id=single.id,
                            reason="Seed evidence",
                            step_type="seed",
                            confidence=0.8,
                        )
                    ],
                    conclusion=conclusion,
                    confidence=0.6,
                    evidence_count=1,
                    reasoning="Single event — limited inference.",
                )
            return DeductionResult(
                chain=[],
                conclusion="Insufficient evidence.",
                confidence=0.0,
                evidence_count=0,
                reasoning="Only one or zero events.",
            )

        # Step 4: Build inference chain
        chain, reasoning = self._build_chain(pool, list(seeds))
        conclusion = self._synthesize_conclusion(pool, chain)
        confidence = self._compute_confidence(chain, pool)

        return DeductionResult(
            chain=chain,
            conclusion=conclusion,
            confidence=confidence,
            evidence_count=len(pool),
            reasoning=reasoning,
        )

    def _resolve_query_to_events(self, query: str, limit: int = 3) -> List[Event]:
        """Resolve text query to closest matching events."""
        query_lower = query.lower()
        query_tokens = set(query_lower.split())
        scored: List[tuple[float, Event]] = []

        for event in self.indb.iter_events():
            event_tokens = set(t.lower() for t in event.raw_data_anchor)
            overlap = len(query_tokens & event_tokens)
            loc_match = 1 if any(qt in event.location.lower() for qt in query_tokens) else 0
            score = overlap * 0.5 + loc_match * 0.5
            if score > 0:
                scored.append((score, event))

        scored.sort(key=lambda x: -x[0])
        return [ev for _, ev in scored[:limit]]

    def _build_chain(
        self,
        pool: List[Event],
        seeds: List[Event],
    ) -> Tuple[List[InferenceStep], str]:
        """Build inference chain from ordered events."""
        seed_ids = {s.id for s in seeds}
        steps: List[InferenceStep] = []
        reasons: List[str] = []

        for i, ev in enumerate(pool):
            if ev.id in seed_ids:
                steps.append(InferenceStep(
                    event_id=ev.id,
                    reason="Seed evidence",
                    step_type="seed",
                    confidence=0.9,
                ))
                reasons.append(f"Seed: {ev.id}")
            else:
                prev = pool[i - 1] if i > 0 else None
                reason, step_type, conf = self._infer_step(ev, prev, pool)
                steps.append(InferenceStep(
                    event_id=ev.id,
                    reason=reason,
                    step_type=step_type,
                    confidence=conf,
                ))
                reasons.append(reason)

        reasoning = " → ".join(reasons[:10])
        if len(reasons) > 10:
            reasoning += " …"
        return steps, reasoning

    def _infer_step(
        self,
        ev: Event,
        prev: Optional[Event],
        pool: List[Event],
    ) -> Tuple[str, str, float]:
        """Infer why this event belongs in the chain."""
        if not prev:
            return "Initial evidence", "seed", 0.8

        # Temporal
        if ev.timestamp > prev.timestamp:
            delta = ev.timestamp - prev.timestamp
            if delta < 3600:  # Within hour
                return f"Temporal: ~{int(delta/60)}min after {prev.id[:8]}…", "temporal", 0.85
            return f"Temporal: after {prev.id[:8]}…", "temporal", 0.75

        # Spatial
        if ev.location == prev.location:
            return f"Spatial: same location as {prev.id[:8]}… ({ev.location})", "spatial", 0.8

        # Token overlap
        tok_a = set(ev.raw_data_anchor)
        tok_b = set(prev.raw_data_anchor)
        shared = tok_a & tok_b
        if shared:
            sample = ", ".join(list(shared)[:3])
            return f"Token: shared [{sample}]", "token", 0.7

        return f"Chronological: follows {prev.id[:8]}…", "temporal", 0.6

    def _synthesize_single(self, ev: Event) -> str:
        """Synthesize conclusion from a single event."""
        tokens = " ".join(ev.raw_data_anchor[:5])
        return f"Single evidence: {ev.location} — {tokens[:80]}{'…' if len(tokens) > 80 else ''}"

    def _synthesize_conclusion(self, pool: List[Event], chain: List[InferenceStep]) -> str:
        """Synthesize conclusion from evidence chain."""
        if not pool:
            return "No conclusion."
        first = pool[0]
        last = pool[-1]
        locations = {e.location for e in pool}
        all_tokens: List[str] = []
        for e in pool:
            all_tokens.extend(e.raw_data_anchor)
        from collections import Counter
        top_tokens = [t for t, _ in Counter(all_tokens).most_common(5)]
        loc_str = ", ".join(list(locations)[:3]) if locations else "unknown"
        token_str = ", ".join(top_tokens[:5]) if top_tokens else "—"
        return (
            f"Evidence suggests a sequence across {len(pool)} events "
            f"at {loc_str}. "
            f"Thematic: {token_str}."
        )

    def _compute_confidence(self, chain: List[InferenceStep], pool: List[Event]) -> float:
        """Compute overall confidence from chain steps."""
        if not chain:
            return 0.0
        avg = sum(s.confidence for s in chain) / len(chain)
        # Bonus for more evidence
        count_bonus = min(0.1, len(pool) * 0.02)
        return min(1.0, avg + count_bonus)
