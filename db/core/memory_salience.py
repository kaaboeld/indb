"""
Memory salience — hot / cold / wake (pure math, no storage side effects).

See docs/MEMORY_LIFECYCLE.md.
"""
from __future__ import annotations

import math
import time
from typing import Any, Optional

from core.constants import (
    MEMORY_HOT_SALIENCE_THRESHOLD,
    MEMORY_RECENCY_TAU_SEC,
    MEMORY_WAKE_ECHO_THRESHOLD,
    MEMORY_WAKE_LOCK_THRESHOLD,
)


def compute_salience(
    event: Any,
    now: Optional[float] = None,
    source_weight: float = 1.0,
) -> float:
    """
    Salience ∈ (0, ~∞); higher = stays hot longer.
    Uses fusion_count and last resonance touch from temporal_metadata.
    """
    now = now if now is not None else time.time()
    fusion = max(0, int(getattr(event, "fusion_count", 0) or 0))
    mass = math.log1p(fusion)

    meta = getattr(event, "temporal_metadata", None) or {}
    last_touch = float(
        meta.get("last_resonance_at")
        or meta.get("last_touch")
        or getattr(event, "timestamp", now)
    )
    age = max(0.0, now - last_touch)
    recency = 1.0 / (1.0 + age / MEMORY_RECENCY_TAU_SEC)

    return mass * source_weight * recency


def is_hot(salience: float) -> bool:
    return salience >= MEMORY_HOT_SALIENCE_THRESHOLD


def should_wake(
    echo_score: float = 0.0,
    lock_score: float = 0.0,
) -> bool:
    """Strong horizontal trigger can pull a cold node back."""
    return (
        echo_score >= MEMORY_WAKE_ECHO_THRESHOLD
        or lock_score >= MEMORY_WAKE_LOCK_THRESHOLD
    )
