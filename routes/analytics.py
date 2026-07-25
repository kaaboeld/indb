"""
Analytics & Fusion Routes (v2)

Handles fusion statistics, pattern analysis, and system reporting.
"""
import time
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException

from core.deps import IndbDep
from core.models import StandardResponse
from services.fusion.metrics import compute_fusion_metrics, is_fused_record

router = APIRouter(prefix="/api/v2", tags=["analytics"])


# ============================================================================
# Fusion Endpoints
# ============================================================================

@router.get("/fusion/stats", response_model=StandardResponse[Dict[str, Any]])
async def fusion_statistics(db: IndbDep):
    """Get Event Fusion statistics (v2)."""
    try:
        from services.fusion.metrics import compute_fusion_metrics
    except ImportError:
        return StandardResponse(
            data={},
            status="error",
            num_errors=1,
            meta={"error": "Event Fusion module not available"},
        )

    metrics = compute_fusion_metrics(list(db.iter_events()))
    data = {
        "summary": {
            "total_events": metrics["total_events"],
            "fused_events": metrics["fused_events"],
            "regular_events": metrics["regular_events"],
            "total_fusions": metrics["total_fusions"],
        },
        "metrics": {
            "fusion_rate": metrics["fusion_rate"],
            "storage_efficiency": metrics["storage_efficiency"],
            "events_saved": metrics["events_saved"],
        },
    }

    return StandardResponse(data=data)


@router.get("/fusion/patterns", response_model=StandardResponse[Dict[str, int]])
async def fusion_patterns(db: IndbDep):
    """Get pattern distribution (v2)."""
    try:
        from services.fusion import FusedEvent
    except ImportError:
        return StandardResponse(
            data={}, status="error", meta={"error": "Event Fusion module not available"}
        )

    fused_events = [e for e in db.iter_events() if is_fused_record(e)]
    patterns: Dict[str, int] = {}
    for event in fused_events:
        pattern = getattr(event, "pattern", "unknown")
        patterns[pattern] = patterns.get(pattern, 0) + 1

    return StandardResponse(data=patterns, meta={"total_fused_events": len(fused_events)})


@router.get("/fusion/top", response_model=StandardResponse[List[Dict[str, Any]]])
async def top_fused_events(db: IndbDep, limit: int = 10):
    """Get top fused events (v2)."""
    try:
        from services.fusion import FusedEvent
    except ImportError:
        return StandardResponse(
            data=[], status="error", meta={"error": "Event Fusion module not available"}
        )

    fused_events = [e for e in db.iter_events() if is_fused_record(e)]
    top = sorted(
        [e for e in fused_events if int(getattr(e, "fusion_count", 0) or 0) > 0],
        key=lambda e: int(getattr(e, "fusion_count", 0) or 0),
        reverse=True,
    )[:limit]

    data = [
        {
            "id": e.id[:8],
            "fusion_count": e.fusion_count,
            "pattern": getattr(e, "pattern", "unknown"),
            "tokens": e.raw_data_anchor[:5],
            "location": e.location,
        }
        for e in top
    ]

    return StandardResponse(data=data, meta={"limit": limit, "count": len(data)})


@router.get("/fusion/neural/patterns", response_model=StandardResponse[Dict[str, Any]])
async def neural_pattern_analysis(db: IndbDep):
    """
    Run Global Neural Pattern Recognition (DBSCAN) on all events.
    """
    start_time = time.time()
    analysis = db.db.detect_patterns()
    duration = time.time() - start_time

    if "patterns" in analysis:
        analysis["meta"] = {
            "duration": f"{duration:.3f}s",
            "method": "DBSCAN",
            "engine": "scikit-learn"
        }

    return StandardResponse(data=analysis)


# ============================================================================
# General Analytics
# ============================================================================

@router.get("/analytics/overview", response_model=StandardResponse[Dict[str, Any]])
async def get_analytics_overview(db: IndbDep):
    """Get comprehensive analytics overview (v2)."""
    return StandardResponse(data=db.db.get_stats())


@router.get("/analytics/report", response_model=StandardResponse[Dict[str, Any]])
async def get_analytics_report(db: IndbDep, format: str = "json"):
    """Get formatted analytics report (v2)."""
    if format == "text":
        report = db.db.get_report("text")
        return StandardResponse(data={"report": report, "format": "text"})
    return StandardResponse(data=db.db.get_stats(), meta={"format": "json"})


@router.get("/analytics/insights", response_model=StandardResponse[List[str]])
async def get_analytics_insights(db: IndbDep):
    """Get actionable insights (v2)."""
    insights = db.db.get_insights()
    return StandardResponse(data=insights, meta={"count": len(insights)})


@router.get("/analytics/database", response_model=StandardResponse[Dict[str, Any]])
async def get_database_stats(db: IndbDep):
    """Get database statistics (v2)."""
    return StandardResponse(data=db.db.analytics.get_database_stats())


@router.get("/analytics/fusion", response_model=StandardResponse[Dict[str, Any]])
async def get_fusion_analytics(db: IndbDep):
    """Get fusion analytics (v2)."""
    return StandardResponse(data=db.db.analytics.get_fusion_stats())


@router.get("/analytics/temporal", response_model=StandardResponse[Dict[str, Any]])
async def get_temporal_analytics(db: IndbDep):
    """Get temporal pattern analytics (v2)."""
    return StandardResponse(data=db.db.analytics.get_temporal_stats())


@router.get("/analytics/tokens", response_model=StandardResponse[Dict[str, Any]])
async def get_token_analytics(db: IndbDep):
    """Get token analysis (v2)."""
    return StandardResponse(data=db.db.analytics.get_token_stats())


@router.get("/analytics/performance", response_model=StandardResponse[Dict[str, Any]])
async def get_performance_metrics(db: IndbDep):
    """Get performance metrics (v2)."""
    return StandardResponse(data=db.db.analytics.get_performance_stats())
