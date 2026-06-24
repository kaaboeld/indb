"""
Fusion Analytics Endpoint

Provides statistics and insights about Event Fusion activity.
"""

from fastapi import APIRouter
from typing import Dict, Any, List
import time

router = APIRouter(prefix="/api/v1/fusion", tags=["fusion"])


def get_fusion_stats(db) -> Dict[str, Any]:
    """
    Calculate fusion statistics from database
    
    Args:
        db: INDB instance
        
    Returns:
        Fusion statistics and metrics
    """
    try:
        from services.fusion.engine import FusedEvent
    except ImportError:
        return {"error": "Event Fusion module not available"}
    
    total_events = len(db.memory)
    fused_events = [e for e in db.memory if isinstance(e, FusedEvent)]
    regular_events = total_events - len(fused_events)
    
    # Calculate total fusion count (how many original events were fused)
    total_fusions = sum(e.fusion_count for e in fused_events)
    
    # Pattern distribution
    patterns = {}
    for event in fused_events:
        pattern = event.temporal_span.get("pattern", "unknown")
        patterns[pattern] = patterns.get(pattern, 0) + 1
    
    # Fusion type distribution
    fusion_types = {}
    for event in fused_events:
        fusion_types[event.fusion_type] = fusion_types.get(event.fusion_type, 0) + 1
    
    # Top fused events (by fusion count)
    top_fused = sorted(fused_events, key=lambda e: e.fusion_count, reverse=True)[:5]
    
    # Token evolution (most common tokens in fused events)
    token_frequency = {}
    for event in fused_events:
        for token in event.raw_data_anchor:
            token_frequency[token] = token_frequency.get(token, 0) + 1
    
    top_tokens = sorted(token_frequency.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Calculate fusion rate
    fusion_rate = (len(fused_events) / total_events * 100) if total_events > 0 else 0
    
    # Storage efficiency (how many events saved by fusion)
    events_saved = total_fusions - len(fused_events)
    storage_efficiency = (events_saved / total_fusions * 100) if total_fusions > 0 else 0
    
    return {
        "summary": {
            "total_events": total_events,
            "fused_events": len(fused_events),
            "regular_events": regular_events,
            "total_fusions": total_fusions,
            "fusion_rate": round(fusion_rate, 2),
            "storage_efficiency": round(storage_efficiency, 2),
            "events_saved": events_saved
        },
        "patterns": patterns,
        "fusion_types": fusion_types,
        "top_fused_events": [
            {
                "id": e.id[:8],
                "fusion_count": e.fusion_count,
                "fusion_type": e.fusion_type,
                "pattern": e.temporal_span.get("pattern", "unknown"),
                "tokens": e.raw_data_anchor[:5],  # First 5 tokens
                "location": e.location
            }
            for e in top_fused
        ],
        "top_tokens": [
            {"token": token, "frequency": freq}
            for token, freq in top_tokens
        ],
        "timestamp": time.time()
    }


@router.get("/stats")
async def fusion_statistics():
    """
    Get Event Fusion statistics
    
    Returns comprehensive fusion metrics including:
    - Total events and fusion rate
    - Pattern distribution
    - Fusion type breakdown
    - Top fused events
    - Token frequency analysis
    """
    from main import db  # Import db from main
    return get_fusion_stats(db)


@router.get("/patterns")
async def fusion_patterns():
    """
    Get pattern distribution analysis
    """
    from main import db
    stats = get_fusion_stats(db)
    return {
        "patterns": stats["patterns"],
        "total_fused_events": stats["summary"]["fused_events"]
    }


@router.get("/top")
async def top_fused_events(limit: int = 10):
    """
    Get top fused events by fusion count
    """
    from main import db
    try:
        from services.fusion.engine import FusedEvent
    except ImportError:
        return {"error": "Event Fusion module not available"}
    
    fused_events = [e for e in db.memory if isinstance(e, FusedEvent)]
    top = sorted(fused_events, key=lambda e: e.fusion_count, reverse=True)[:limit]
    
    return {
        "top_fused_events": [
            {
                "id": e.id,
                "fusion_count": e.fusion_count,
                "fusion_type": e.fusion_type,
                "pattern": e.temporal_span.get("pattern", "unknown"),
                "tokens": e.raw_data_anchor,
                "token_weights": e.token_weights,
                "location": e.location,
                "temporal_span": e.temporal_span
            }
            for e in top
        ],
        "total": len(top)
    }


@router.get("/neural/patterns")
async def neural_pattern_analysis():
    """
    Run Global Neural Pattern Recognition (DBSCAN) on all events.
    """
    from main import db
    
    start_time = time.time()
    analysis = db.detect_patterns()
    duration = time.time() - start_time
    
    # Add metadata
    if "patterns" in analysis:
        analysis["meta"] = {
            "duration": f"{duration:.3f}s",
            "method": "DBSCAN",
            "engine": "scikit-learn"
        }
    
    return analysis
