"""Shared fusion classification and metrics for analytics endpoints."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Sequence


def is_fused_record(event: Any) -> bool:
    """
    True when an event is a fusion product, not merely carrying a fusion_count field.

    Regular Event instances always expose fusion_count=0; only merged/FusedEvent rows count.
    """
    try:
        from services.fusion.engine import FusedEvent

        if isinstance(event, FusedEvent):
            return True
    except ImportError:
        pass

    if bool(getattr(event, "is_fused", False)):
        return True

    return int(getattr(event, "fusion_count", 0) or 0) > 0


def compute_fusion_metrics(events: Sequence[Any]) -> Dict[str, Any]:
    """
    Compute fusion metrics with one consistent definition across endpoints.

    Definitions:
    - fused_events: stored records produced by fusion (FusedEvent or is_fused / fusion_count>0)
    - total_fusions: sum of fusion_count on fused records (ingestions absorbed into survivors)
    - events_saved: duplicate ingestions merged away (total_fusions - fused_events)
    - fusion_rate: fused records / total records (%)
    - storage_efficiency: events_saved / total_fusions (%), 0 when no merges occurred
    """
    all_events = list(events)
    total_events = len(all_events)
    fused_events = [e for e in all_events if is_fused_record(e)]
    regular_events = total_events - len(fused_events)

    total_fusions = sum(int(getattr(e, "fusion_count", 0) or 0) for e in fused_events)
    events_saved = max(0, total_fusions - len(fused_events))

    fusion_rate = (len(fused_events) / total_events * 100) if total_events else 0.0
    storage_efficiency = (events_saved / total_fusions * 100) if total_fusions > 0 else 0.0

    merged_events = [
        e for e in fused_events if int(getattr(e, "fusion_count", 0) or 0) > 0
    ]
    top_fused = sorted(
        merged_events,
        key=lambda e: int(getattr(e, "fusion_count", 0) or 0),
        reverse=True,
    )[:5]

    fusion_types: Dict[str, int] = {}
    patterns: Dict[str, int] = {}
    for event in fused_events:
        fusion_type = getattr(event, "fusion_type", None)
        if fusion_type:
            fusion_types[fusion_type] = fusion_types.get(fusion_type, 0) + 1

        pattern = getattr(event, "pattern", None)
        if not pattern and hasattr(event, "temporal_span"):
            pattern = (event.temporal_span or {}).get("pattern")
        if pattern:
            patterns[pattern] = patterns.get(pattern, 0) + 1

    return {
        "enabled": total_fusions > 0 or len(fused_events) > 0,
        "total_events": total_events,
        "regular_events": regular_events,
        "fused_events": len(fused_events),
        "total_fused": len(fused_events),
        "total_fusions": total_fusions,
        "fusion_rate": round(fusion_rate, 2),
        "storage_efficiency": round(storage_efficiency, 2),
        "events_saved": events_saved,
        "fusion_types": fusion_types,
        "patterns": patterns,
        "top_fused": [
            {
                "id": e.id[:8],
                "fusion_count": int(getattr(e, "fusion_count", 0) or 0),
                "pattern": getattr(e, "pattern", None)
                or (getattr(e, "temporal_span", None) or {}).get("pattern", "unknown"),
                "tokens": list(getattr(e, "raw_data_anchor", []))[:5],
                "location": getattr(e, "location", None),
            }
            for e in top_fused
        ],
    }
