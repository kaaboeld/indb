"""
Analytics API endpoints for INDB

Provides database-level analytics and reporting.
"""

from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


@router.get("/overview")
async def get_analytics_overview():
    """
    Get comprehensive analytics overview.
    
    Returns all key metrics: database stats, fusion stats,
    temporal patterns, token analysis, and performance.
    """
    from main import kernel
    stats = kernel.db.get_stats()
    return stats


@router.get("/report")
async def get_analytics_report(format: str = "json"):
    """
    Get formatted analytics report.
    
    Args:
        format: "text" or "json"
    
    Returns:
        Formatted report
    """
    from main import kernel
    
    if format == "text":
        report = kernel.db.get_report("text")
        return {"report": report}
    else:
        return kernel.db.get_stats()


@router.get("/insights")
async def get_analytics_insights():
    """
    Get actionable insights based on current data.
    
    Returns:
        List of insight strings
    """
    from main import kernel
    insights = kernel.db.get_insights()
    return {"insights": insights, "count": len(insights)}


@router.get("/database")
async def get_database_stats():
    """Get database statistics only."""
    from main import kernel
    return kernel.db.analytics.get_database_stats()


@router.get("/fusion")
async def get_fusion_analytics():
    """Get fusion analytics only."""
    from main import kernel
    return kernel.db.analytics.get_fusion_stats()


@router.get("/temporal")
async def get_temporal_analytics():
    """Get temporal pattern analytics."""
    from main import kernel
    return kernel.db.analytics.get_temporal_stats()


@router.get("/tokens")
async def get_token_analytics():
    """Get token analysis."""
    from main import kernel
    return kernel.db.analytics.get_token_stats()


@router.get("/performance")
async def get_performance_metrics():
    """Get performance metrics."""
    from main import kernel
    return kernel.db.analytics.get_performance_stats()
