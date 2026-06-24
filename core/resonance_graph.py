"""
ResonanceGraph — materialized horizontal edges (seed → targets).

Persisted to disk; used to narrow Echo scans to known neighbors.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional, Set

from core.constants import (
    RESONANCE_GRAPH_ENABLED_DEFAULT,
    RESONANCE_GRAPH_MAX_EDGES_PER_SEED,
    RESONANCE_GRAPH_STALE_SEC,
)
from core.echo import ResonanceResult
from storage.resonance_graph_store import load_edges, save_edges

logger = logging.getLogger("indb.resonance_graph")


def _graph_enabled() -> bool:
    return os.getenv("RESONANCE_GRAPH_ENABLED", str(RESONANCE_GRAPH_ENABLED_DEFAULT)).lower() == "true"


class ResonanceGraph:
    """Adjacency from seed event id to scored target links."""

    def __init__(self, edges: Optional[Dict[str, List[Dict[str, Any]]]] = None) -> None:
        self._edges: Dict[str, List[Dict[str, Any]]] = edges if edges is not None else {}
        self._dirty = False

    @classmethod
    def load(cls) -> "ResonanceGraph":
        if not _graph_enabled():
            return cls({})
        return cls(load_edges())

    def neighbor_ids(
        self,
        seed_id: str,
        min_score: float = 0.0,
        limit: int = 50,
        max_age_sec: Optional[float] = None,
    ) -> List[str]:
        """O(neighbors) lookup of cached targets for a seed."""
        if not _graph_enabled():
            return []
        age_limit = max_age_sec if max_age_sec is not None else RESONANCE_GRAPH_STALE_SEC
        now = time.time()
        rows = self._edges.get(seed_id, [])
        out: List[tuple[float, str]] = []
        for row in rows:
            if row.get("score", 0) < min_score:
                continue
            ts = row.get("ts", 0)
            if age_limit > 0 and ts and (now - ts) > age_limit:
                continue
            out.append((float(row["score"]), row["target_id"]))
        out.sort(key=lambda x: x[0], reverse=True)
        return [eid for _, eid in out[:limit]]

    def record_wave(self, seed_id: str, results: List[ResonanceResult]) -> None:
        if not _graph_enabled() or not results:
            return
        now = time.time()
        bucket: List[Dict[str, Any]] = []
        for r in results[:RESONANCE_GRAPH_MAX_EDGES_PER_SEED]:
            bucket.append({
                "target_id": r.event_id,
                "score": round(r.score, 4),
                "harmonic_type": r.harmonic_type,
                "reason": r.reason,
                "ts": now,
            })
        self._edges[seed_id] = bucket
        self._dirty = True

    def persist_if_dirty(self) -> None:
        if not _graph_enabled() or not self._dirty:
            return
        try:
            save_edges(self._edges)
            self._dirty = False
            logger.debug("ResonanceGraph persisted (%d seeds)", len(self._edges))
        except Exception as e:
            logger.warning("ResonanceGraph persist failed: %s", e)

    def prune_missing(self, valid_ids: Set[str]) -> None:
        """Drop edges pointing at events no longer in memory."""
        if not self._edges:
            return
        changed = False
        for seed_id in list(self._edges.keys()):
            if seed_id not in valid_ids:
                del self._edges[seed_id]
                changed = True
                continue
            kept = [e for e in self._edges[seed_id] if e.get("target_id") in valid_ids]
            if len(kept) != len(self._edges[seed_id]):
                self._edges[seed_id] = kept
                changed = True
            if not self._edges[seed_id]:
                del self._edges[seed_id]
        if changed:
            self._dirty = True

    def stats(self) -> Dict[str, Any]:
        total = sum(len(v) for v in self._edges.values())
        return {
            "enabled": _graph_enabled(),
            "seed_count": len(self._edges),
            "edge_count": total,
            "dirty": self._dirty,
        }

    def get_edges(self, seed_id: str) -> List[Dict[str, Any]]:
        return list(self._edges.get(seed_id, []))
