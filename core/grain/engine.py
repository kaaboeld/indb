"""
Grain Engine — orchestrates verification across the noise-tolerance spectrum.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from core.echo import ResonanceEngine
from core.event import Event
from core.grain.exact import verify_exact
from core.grain.models import GrainConfig, GrainResult, GrainTier, TIER_CATALOG
from core.grain.redundant import verify_redundant
from core.grain.resonant import verify_resonant
from core.grain.statistical import verify_statistical

logger = logging.getLogger("indb.grain")


class GrainEngine:
    """
    Identity verification across the noise-tolerance axis.

    Grain answers: "Is this the same origin, and how sure are we — given noise?"
    Unlike Echo (meaning/resonance) or signing (binary axiom), Grain unifies
    exact, redundant, resonant, and statistical tiers under one API.
    """

    def __init__(self, indb_instance=None):
        self.indb = indb_instance
        self._echo = ResonanceEngine(indb_instance)

    def _resolve_event(self, event_id: str) -> Optional[Event]:
        if self.indb is None:
            return None
        if hasattr(self.indb, "get_event"):
            return self.indb.get_event(event_id)
        if hasattr(self.indb, "get_event_by_id"):
            return self.indb.get_event_by_id(event_id)
        return None

    def _resolve_reputation(self, event: Event) -> float:
        if not self.indb or not event.source_id:
            return 0.5
        db = getattr(self.indb, "db", self.indb)
        if hasattr(db, "get_source"):
            source = db.get_source(event.source_id)
            if source:
                return source.reputation
        return 0.5

    def _events_for_key_id(self, key_id: str) -> List[Event]:
        if not self.indb:
            return []
        matches: List[Event] = []
        for event in self.indb.iter_events():
            sig = event.signature or {}
            if sig.get("key_id") == key_id:
                matches.append(event)
        return matches

    def select_tier(
        self,
        candidate: Dict[str, Any],
        reference_event: Optional[Event] = None,
        reference_events: Optional[List[Event]] = None,
        config: Optional[GrainConfig] = None,
    ) -> GrainTier:
        """Auto-select tier based on available evidence."""
        config = config or GrainConfig()

        sig = candidate.get("signature")
        if isinstance(sig, dict) and sig.get("signature"):
            return GrainTier.EXACT

        ref_list = reference_events or []
        if reference_event and reference_event not in ref_list:
            ref_list = [reference_event] + ref_list

        if len(ref_list) >= config.min_events and all(
            (e.signature for e in ref_list)
        ):
            return GrainTier.REDUNDANT

        total_tokens = sum(len(e.raw_data_anchor or []) for e in ref_list)
        if reference_event:
            total_tokens = max(
                total_tokens,
                len(reference_event.raw_data_anchor or []),
            )
        cand_tokens = candidate.get("raw_data_anchor") or []
        if (
            total_tokens >= config.min_tokens
            and len(cand_tokens) >= max(5, config.min_tokens // 4)
            and len(ref_list) >= 2
        ):
            return GrainTier.STATISTICAL

        return GrainTier.RESONANT

    def verify(
        self,
        candidate: Dict[str, Any],
        reference_event_id: Optional[str] = None,
        reference_event_ids: Optional[List[str]] = None,
        expected_key_id: Optional[str] = None,
        config: Optional[GrainConfig] = None,
    ) -> GrainResult:
        """
        Verify candidate identity against reference(s).

        candidate: event dict or partial event with raw_data_anchor (+ optional signature)
        reference_event_id: primary seed event for resonant/statistical tiers
        reference_event_ids: cluster for redundant tier
        expected_key_id: constrain exact/redundant to this public identity
        """
        config = config or GrainConfig()

        reference_event = (
            self._resolve_event(reference_event_id) if reference_event_id else None
        )
        reference_events: List[Event] = []
        if reference_event_ids:
            for eid in reference_event_ids:
                ev = self._resolve_event(eid)
                if ev:
                    reference_events.append(ev)
        if reference_event and reference_event not in reference_events:
            reference_events.insert(0, reference_event)

        tier = (
            config.tier
            if config.tier != "auto"
            else self.select_tier(candidate, reference_event, reference_events, config)
        )

        logger.debug("Grain verify tier=%s reference=%s", tier, reference_event_id)

        if tier == GrainTier.EXACT:
            return verify_exact(candidate, expected_key_id=expected_key_id)

        if tier == GrainTier.REDUNDANT:
            event_dicts = [e.to_dict() for e in reference_events]
            if candidate.get("signature") and candidate not in event_dicts:
                event_dicts.append(candidate)
            if not event_dicts and candidate.get("signature"):
                event_dicts = [candidate]
            return verify_redundant(event_dicts, expected_key_id=expected_key_id, config=config)

        if tier == GrainTier.STATISTICAL:
            if not reference_events and reference_event:
                reference_events = [reference_event]
            if expected_key_id and not reference_events:
                reference_events = self._events_for_key_id(expected_key_id)
            if not reference_events:
                return GrainResult(
                    tier_used=GrainTier.STATISTICAL,
                    match_score=0.0,
                    verdict="insufficient_signal",
                    insufficient_signal=True,
                    false_accept_risk=0.0,
                    false_reject_risk=1.0,
                    insight="No reference cluster for statistical tier.",
                )
            cand_event = (
                Event.from_dict(candidate)
                if "location" in candidate
                else Event(
                    raw_data_anchor=candidate.get("raw_data_anchor", []),
                    location=candidate.get("location", "grain/verify"),
                )
            )
            return verify_statistical(reference_events, cand_event, config=config)

        # RESONANT (default)
        if not reference_event:
            return GrainResult(
                tier_used=GrainTier.RESONANT,
                match_score=0.0,
                verdict="insufficient_signal",
                insufficient_signal=True,
                false_accept_risk=0.0,
                false_reject_risk=1.0,
                insight="Resonant tier requires reference_event_id.",
            )

        cand_event = (
            Event.from_dict(candidate)
            if "location" in candidate
            else Event(
                raw_data_anchor=candidate.get("raw_data_anchor", []),
                location=candidate.get("location", reference_event.location),
            )
        )
        reputation = self._resolve_reputation(reference_event)
        if candidate.get("source_id"):
            cand_rep = self._resolve_reputation(
                Event(raw_data_anchor=[], location="", source_id=candidate["source_id"])
            )
            reputation = (reputation + cand_rep) / 2

        return verify_resonant(
            reference_event,
            cand_event,
            self._echo,
            reputation=reputation,
            config=config,
        )

    @staticmethod
    def list_tiers():
        return TIER_CATALOG
