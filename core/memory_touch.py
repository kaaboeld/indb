"""
Touch last_resonance_at when horizontal engines run (Echo, Subwave).

In-memory by default; optional disk persist via MEMORY_TOUCH_PERSIST_ON_RESONANCE.
"""
from __future__ import annotations

import time
from typing import Any, Iterable, Optional

from core.constants import MEMORY_TOUCH_PERSIST_ON_RESONANCE


def touch_resonance(event: Any, now: Optional[float] = None) -> None:
    if event is None:
        return
    now = now if now is not None else time.time()
    meta = getattr(event, "temporal_metadata", None)
    if meta is None:
        event.temporal_metadata = {}
        meta = event.temporal_metadata
    meta["last_resonance_at"] = now


def touch_resonance_events(
    indb: Any,
    events: Iterable[Any],
    *,
    persist: Optional[bool] = None,
) -> int:
    """Touch each event; optionally persist via indb.update_event."""
    persist = (
        MEMORY_TOUCH_PERSIST_ON_RESONANCE if persist is None else persist
    )
    count = 0
    for event in events:
        if event is None:
            continue
        touch_resonance(event)
        count += 1
        if persist and hasattr(indb, "update_event"):
            indb.update_event(event)
    return count
