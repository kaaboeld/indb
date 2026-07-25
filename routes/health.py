"""
Health & Monitoring Routes (v2)

Handles system health checks and status reporting.
"""
from typing import Dict, Any
from fastapi import APIRouter

from core.constants import VERSION
from core.deps import IndbDep
from core.models import StandardResponse, HealthStatus
from services import ML_AVAILABLE

router = APIRouter()  # Tags and prefix handled per route or in main

@router.get("/health", tags=["health"])
async def simple_health():
    """Simple health check (v1 compatible)."""
    return {"status": "ok", "version": VERSION}


@router.get("/api/v2/health", response_model=StandardResponse[HealthStatus], tags=["health"])
async def health_check_v2(db: IndbDep):
    """
    Get system health status.
    """
    try:
        db._check_initialized()
    except Exception:
        return StandardResponse(
            status="error",
            message="Database not initialized",
            data=HealthStatus(
                project={"name": "INDB", "version": VERSION},
                status="maintenance",
                database={},
                components={},
                endpoints={},
            )
        )

    # Get real database stats
    stats = db.db.get_stats()
    insights = db.db.get_insights()

    data = HealthStatus(
        project={"name": "INDB", "version": VERSION, "codename": "Alpha"},
        status="operational",
        health_score=stats.get("health_score"),
        oom_prediction=stats.get("oom_prediction"),
        database={
            "total_events": db.get_event_count(),
            "fused_events": stats["database"]["fused_events"],
            "fusion_rate": f"{stats['fusion']['fusion_rate']}%",
            "storage_efficiency": f"{stats['fusion']['storage_efficiency']}%",
            "events_saved": stats["fusion"]["events_saved"],
            "unique_locations": stats["database"]["unique_locations"],
        },
        components={
            "event_fusion": {
                "enabled": True,
                "status": "operational",
                "rate": stats["fusion"]["fusion_rate"],
            },
            "analytics": {
                "enabled": True,
                "status": "operational",
                "insights_count": len(insights),
            },
            "ml_services": {
                "enabled": ML_AVAILABLE,
                "status": "operational" if ML_AVAILABLE else "not_installed",
            },
        },
        system=stats.get("system_health"),
        endpoints={
            "docs": "/docs",
            "health": "/api/v2/health",
            "events": "/api/v2/events",
            "search": "/api/v2/search",
            "interpret": "/api/v2/interpret",
            "analytics": "/api/v2/analytics/overview",
            "fusion": "/api/v2/fusion/stats",
            "export_json": "/api/v2/export/json",
            "export_csv": "/api/v2/export/csv",
            "websocket": "/ws",
            "websocket_stats": "/api/v2/websocket/stats",
            "advanced_query": "/api/v2/events/query",
        },
    )

    return StandardResponse(data=data, meta={"insights_preview": insights[:3] if insights else []})
