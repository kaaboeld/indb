"""
Semantic neighbor discovery — embedding-based horizontal candidates.

Optional: requires sentence-transformers (services.ML_AVAILABLE).
"""
from __future__ import annotations

import logging
import os
from typing import Callable, List, Optional, Set

from core.constants import (
    RESONANCE_SEMANTIC_ENABLED_DEFAULT,
    RESONANCE_SEMANTIC_POOL_CAP,
    RESONANCE_SEMANTIC_THRESHOLD,
    RESONANCE_SEMANTIC_TOP_K,
)
from core.event import Event

logger = logging.getLogger("indb.semantic_neighbors")

_embeddings = None


def _semantic_enabled() -> bool:
    if os.getenv("RESONANCE_SEMANTIC_ENABLED", str(RESONANCE_SEMANTIC_ENABLED_DEFAULT)).lower() != "true":
        return False
    try:
        from services import ML_AVAILABLE
        return ML_AVAILABLE
    except ImportError:
        return False


def _get_embeddings():
    global _embeddings
    if _embeddings is None:
        from services.ml.embeddings import SemanticEmbeddings
        _embeddings = SemanticEmbeddings()
    return _embeddings


def semantic_candidate_ids(
    seed: Event,
    pool_ids: Set[str],
    resolve_event: Callable[[str], Optional[Event]],
    cap: int = RESONANCE_SEMANTIC_TOP_K,
) -> Set[str]:
    """
    From a pool of event ids, return top semantic neighbors of seed (cosine similarity).
    """
    if not _semantic_enabled() or not pool_ids:
        return set()

    try:
        emb = _get_embeddings()
    except Exception as e:
        logger.debug("Semantic neighbors unavailable: %s", e)
        return set()

    scored: List[tuple[float, str]] = []
    checked = 0
    for eid in pool_ids:
        if eid == seed.id:
            continue
        ev = resolve_event(eid)
        if not ev or not ev.raw_data_anchor:
            continue
        sim = emb.calculate_similarity(seed.raw_data_anchor, ev.raw_data_anchor)
        if sim >= RESONANCE_SEMANTIC_THRESHOLD:
            scored.append((sim, eid))
        checked += 1
        if checked >= RESONANCE_SEMANTIC_POOL_CAP:
            break

    scored.sort(key=lambda x: x[0], reverse=True)
    return {eid for _, eid in scored[:cap]}


def expand_pool_from_memory(
    seed: Event,
    iter_events: Callable,
    existing: Set[str],
    cap: int = RESONANCE_SEMANTIC_POOL_CAP,
) -> Set[str]:
    """Widen candidate pool for semantic scan when token index is sparse."""
    pool = set(existing)
    if len(pool) >= cap // 2:
        return pool
    for event in iter_events():
        if event.id == seed.id:
            continue
        pool.add(event.id)
        if len(pool) >= cap:
            break
    return pool
