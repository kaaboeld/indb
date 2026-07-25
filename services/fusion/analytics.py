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
        from services.fusion.metrics import compute_fusion_metrics, is_fused_record
    except ImportError:
        return {"error": "Event Fusion module not available"}

    metrics = compute_fusion_metrics(db.memory)
    fused_events = [e for e in db.memory if is_fused_record(e)]

    token_frequency = {}
    for event in fused_events:
        for token in event.raw_data_anchor:
            token_frequency[token] = token_frequency.get(token, 0) + 1

    top_tokens = sorted(token_frequency.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "summary": {
            "total_events": metrics["total_events"],
            "fused_events": metrics["fused_events"],
            "regular_events": metrics["regular_events"],
            "total_fusions": metrics["total_fusions"],
            "fusion_rate": metrics["fusion_rate"],
            "storage_efficiency": metrics["storage_efficiency"],
            "events_saved": metrics["events_saved"],
        },
        "patterns": metrics["patterns"],
        "fusion_types": metrics["fusion_types"],
        "top_fused_events": metrics["top_fused"],
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
        from services.fusion.metrics import is_fused_record
    except ImportError:
        return {"error": "Event Fusion module not available"}
    
    fused_events = [e for e in db.memory if is_fused_record(e)]
    top = sorted(
        [e for e in fused_events if int(getattr(e, "fusion_count", 0) or 0) > 0],
        key=lambda e: int(getattr(e, "fusion_count", 0) or 0),
        reverse=True,
    )[:limit]
    
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
