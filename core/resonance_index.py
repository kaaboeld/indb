"""
ResonanceIndex — horizontal lookup from a seed (raised brick).

Inverted index over event tokens and locations. Echo uses candidate sets
instead of full-memory scans where possible.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Set

from core.constants import RESONANCE_INDEX_MAX_CANDIDATES
from core.event import Event

logger = logging.getLogger("indb.resonance_index")


def _token_keys(raw_anchor: Iterable[str]) -> Set[str]:
    keys: Set[str] = set()
    for token in raw_anchor:
        t = token.lower().strip()
        if not t:
            continue
        keys.add(t)
        if ":" in t:
            parts = t.split(":", 1)
            if len(parts) > 1 and parts[1]:
                keys.add(parts[1])
    return keys


class ResonanceIndex:
    """Token and location inverted index for O(candidates) resonance scans."""

    def __init__(self) -> None:
        self._by_token: Dict[str, Set[str]] = defaultdict(set)
        self._by_location: Dict[str, Set[str]] = defaultdict(set)
        self._event_tokens: Dict[str, Set[str]] = {}

    def clear(self) -> None:
        self._by_token.clear()
        self._by_location.clear()
        self._event_tokens.clear()

    def index(self, event: Event) -> None:
        self.unindex(event.id)
        eid = event.id
        tokens = _token_keys(event.raw_data_anchor)
        self._event_tokens[eid] = tokens
        for key in tokens:
            self._by_token[key].add(eid)
        loc = (event.location or "").strip().lower()
        if loc:
            self._by_location[loc].add(eid)

    def unindex(self, event_id: str) -> None:
        old_tokens = self._event_tokens.pop(event_id, None)
        if old_tokens:
            for key in old_tokens:
                bucket = self._by_token.get(key)
                if bucket:
                    bucket.discard(event_id)
                    if not bucket:
                        del self._by_token[key]
        for loc, ids in list(self._by_location.items()):
            ids.discard(event_id)
            if not ids:
                del self._by_location[loc]

    def rebuild(self, events: Iterable[Event]) -> None:
        self.clear()
        for event in events:
            self.index(event)
        logger.debug("ResonanceIndex rebuilt (%d events)", len(self._event_tokens))

    def token_ids(self, seed: Event) -> Set[str]:
        """Events that share a token with the seed. Location is not enough."""
        out: Set[str] = set()
        for key in _token_keys(seed.raw_data_anchor):
            out |= self._by_token.get(key, set())
        out.discard(seed.id)
        return out

    def candidate_ids(self, seed: Event, cap: int = RESONANCE_INDEX_MAX_CANDIDATES) -> Set[str]:
        """
        Horizontal slice: union of events sharing tokens or location with seed.
        """
        out: Set[str] = set()
        seed_tokens = _token_keys(seed.raw_data_anchor)
        for key in seed_tokens:
            out |= self._by_token.get(key, set())
            if len(out) >= cap:
                break
        loc = (seed.location or "").strip().lower()
        if loc:
            out |= self._by_location.get(loc, set())
        out.discard(seed.id)
        if len(out) > cap:
            # Stable trim: prefer ids that share more tokens with seed
            scored = []
            for eid in out:
                overlap = len(seed_tokens & self._event_tokens.get(eid, set()))
                scored.append((overlap, eid))
            scored.sort(reverse=True)
            out = {eid for _, eid in scored[:cap]}
        return out
