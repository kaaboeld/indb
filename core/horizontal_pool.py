"""
Horizontal candidate pool — union of graph, causal, index, and semantic neighbors.

Shared by Echo and Subwave (one anchor, many nodes answer on the same slice).
"""
from __future__ import annotations

import logging
from typing import Callable, List, Optional, Set

from core.event import Event

logger = logging.getLogger("indb.horizontal_pool")


def collect_candidate_ids(
    indb,
    seed: Event,
    radius: float,
    limit: int,
    resolve_event: Callable[[str], Optional[Event]],
) -> tuple[Set[str], str]:
    """Union horizontal sources; returns (ids, scan_mode label)."""
    candidate_ids: Set[str] = set()
    modes: List[str] = []

    db = getattr(indb, "db", indb)

    graph = getattr(db, "resonance_graph", None)
    if graph is not None:
        cached = graph.neighbor_ids(seed.id, min_score=radius, limit=limit * 2)
        if cached:
            candidate_ids |= set(cached)
            modes.append("graph")

    causal = getattr(db, "causal_index", None)
    if causal is not None:
        causal_ids = causal.neighbor_ids(seed.id, direction="both", limit=limit * 2)
        if causal_ids:
            candidate_ids |= causal_ids
            modes.append("causal")

    index = getattr(db, "resonance_index", None)
    index_ids: Set[str] = set()
    if index is not None:
        index_ids = index.candidate_ids(seed)
        candidate_ids |= index_ids
        modes.append("index")

    wake = getattr(db, "wake_candidates", None)
    if wake is not None:
        try:
            woken = wake(seed)
        except Exception as e:
            logger.debug("Cold wake skipped: %s", e)
            woken = []
        if woken:
            candidate_ids |= set(woken)
            modes.append("wake")

    try:
        from core.semantic_neighbors import expand_pool_from_memory, semantic_candidate_ids

        pool = set(candidate_ids) | index_ids
        if hasattr(indb, "iter_events"):
            pool = expand_pool_from_memory(seed, indb.iter_events, pool)
        elif hasattr(db, "iter_events"):
            pool = expand_pool_from_memory(seed, db.iter_events, pool)
        semantic_ids = semantic_candidate_ids(seed, pool, resolve_event)
        if semantic_ids:
            candidate_ids |= semantic_ids
            modes.append("semantic")
    except Exception as e:
        logger.debug("Semantic neighbor pass skipped: %s", e)

    mode = "+".join(modes) if modes else "full"
    return candidate_ids, mode
