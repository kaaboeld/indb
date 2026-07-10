"""
CausalIndex — lightweight temporal / co-location links (horizontal time slice).

Not full causal inference; materialized next/prev links inside time windows.
"""
from __future__ import annotations

import logging
import os
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Set

from core.constants import (
    CAUSAL_INDEX_ENABLED_DEFAULT,
    CAUSAL_INDEX_MAX_LINKS_PER_EVENT,
    CAUSAL_TIME_WINDOW_SEC,
)
from core.event import Event
from storage.causal_graph_store import load_causal, save_causal

logger = logging.getLogger("indb.causal_index")


def _causal_enabled() -> bool:
    return os.getenv("CAUSAL_INDEX_ENABLED", str(CAUSAL_INDEX_ENABLED_DEFAULT)).lower() == "true"


class CausalIndex:
    def __init__(
        self,
        after: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        before: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> None:
        self._after: Dict[str, List[Dict[str, Any]]] = after or {}
        self._before: Dict[str, List[Dict[str, Any]]] = before or {}
        self._dirty = False

    @classmethod
    def load(cls) -> "CausalIndex":
        if not _causal_enabled():
            return cls()
        data = load_causal()
        return cls(after=data.get("after"), before=data.get("before"))

    def rebuild(self, events: Iterable[Event]) -> None:
        if not _causal_enabled():
            return
        window = CAUSAL_TIME_WINDOW_SEC
        after: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        before: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        by_loc: Dict[str, List[Event]] = defaultdict(list)
        for event in events:
            loc = (event.location or "").strip() or "_"
            by_loc[loc].append(event)

        for _loc, group in by_loc.items():
            group.sort(key=lambda e: e.timestamp)
            for i in range(len(group) - 1):
                a, b = group[i], group[i + 1]
                delta = b.timestamp - a.timestamp
                if delta > window:
                    continue
                link = {
                    "target_id": b.id,
                    "delta_sec": round(delta, 3),
                    "reason": "temporal_sequence",
                }
                if len(after[a.id]) < CAUSAL_INDEX_MAX_LINKS_PER_EVENT:
                    after[a.id].append(link)
                blink = {
                    "target_id": a.id,
                    "delta_sec": round(delta, 3),
                    "reason": "temporal_sequence",
                }
                if len(before[b.id]) < CAUSAL_INDEX_MAX_LINKS_PER_EVENT:
                    before[b.id].append(blink)

        self._after = dict(after)
        self._before = dict(before)
        self._dirty = True
        logger.debug(
            "CausalIndex rebuilt (%d after seeds, %d before seeds)",
            len(self._after),
            len(self._before),
        )

    def links_after(self, event_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        return list(self._after.get(event_id, []))[:limit]

    def links_before(self, event_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        return list(self._before.get(event_id, []))[:limit]

    def neighbor_ids(self, event_id: str, direction: str = "both", limit: int = 20) -> Set[str]:
        out: Set[str] = set()
        if direction in ("after", "both"):
            for row in self.links_after(event_id, limit):
                out.add(row["target_id"])
        if direction in ("before", "both"):
            for row in self.links_before(event_id, limit):
                out.add(row["target_id"])
        return out

    def prune_missing(self, valid_ids: Set[str]) -> None:
        changed = False
        for store in (self._after, self._before):
            for eid in list(store.keys()):
                if eid not in valid_ids:
                    del store[eid]
                    changed = True
                    continue
                kept = [r for r in store[eid] if r.get("target_id") in valid_ids]
                if len(kept) != len(store[eid]):
                    store[eid] = kept
                    changed = True
                if not store[eid]:
                    del store[eid]
        if changed:
            self._dirty = True

    def persist_if_dirty(self) -> None:
        if not _causal_enabled() or not self._dirty:
            return
        try:
            save_causal(self._after, self._before)
            self._dirty = False
        except Exception as e:
            logger.warning("CausalIndex persist failed: %s", e)

    def stats(self) -> Dict[str, Any]:
        return {
            "enabled": _causal_enabled(),
            "after_seeds": len(self._after),
            "before_seeds": len(self._before),
            "dirty": self._dirty,
        }
