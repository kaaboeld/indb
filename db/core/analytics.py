"""
Analytics Engine for INDB

Database-level analytics and reporting system.
Provides insights into events, patterns, fusion, and performance.
"""

from typing import Dict, List, Any, Optional
from collections import Counter, defaultdict
from datetime import datetime
import time

from core.constants import (
    ANALYTICS_SYSTEM_HISTORY_LIMIT,
    ANALYTICS_QUERY_HISTORY_LIMIT,
    ANALYTICS_FUSION_HISTORY_LIMIT,
    ANALYTICS_COGNITIVE_HISTORY_LIMIT,
    ANALYTICS_INSIGHT_EVENT_THRESHOLD,
    ANALYTICS_INSIGHT_LATENCY_WARN_MS,
    ANALYTICS_INSIGHT_LATENCY_GOOD_MS,
)
from prometheus_client import Gauge
import psutil

# Cognitive Metrics
COGNITIVE_LOAD = Gauge("indb_cognitive_load", "Current cognitive load (complexity)")
MEMORY_RESONANCE = Gauge("indb_memory_resonance", "Average memory resonance score")

class INDBAnalytics:
    """
    Comprehensive analytics engine for INDB.

    Provides real-time insights into:
    - Event statistics
    - Fusion metrics
    - Temporal patterns
    - Token analysis
    - Performance metrics
    """

    def __init__(self, db):
        """
        Initialize analytics engine.

        Args:
            db: INDB instance to analyze
        """
        self.db = db
        self.query_times = []
        self.fusion_history = []
        self.cognitive_history = []
        self.system_history = [] # Added for Autonomous Metrics

    def get_overview(self) -> Dict[str, Any]:
        """
        Get comprehensive database overview.

        Returns:
            Dictionary with all key metrics
        """
        return {
            "health_score": self.calculate_health_score(),
            "oom_prediction": self.predict_oom(),
            "database": self.get_database_stats(),
            "fusion": self.get_fusion_stats(),
            "temporal": self.get_temporal_stats(),
            "tokens": self.get_token_stats(),
            "performance": self.get_performance_stats(),
            "cognitive": self.get_cognitive_stats(),
            "system_health": self.get_system_health(),
        }

    def get_system_health(self) -> Dict[str, Any]:
        """Get system resource usage statistics for auto-tuning."""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            
            metrics = {
                "cpu_percent": process.cpu_percent(interval=None),
                "memory_rss_mb": memory_info.rss / 1024 / 1024,
                "memory_percent": process.memory_percent(),
                "timestamp": time.time()
            }
            
            # Update history for prediction
            self.system_history.append(metrics)
            if len(self.system_history) > ANALYTICS_SYSTEM_HISTORY_LIMIT:
                self.system_history = self.system_history[-ANALYTICS_SYSTEM_HISTORY_LIMIT:]
                
            return metrics
        except Exception as e:
            logging.getLogger("indb.analytics").warning(
                "Could not collect system metrics: %s", e
            )
            return {
                "cpu_percent": 0.0,
                "memory_rss_mb": 0.0,
                "memory_percent": 0.0,
                "error": str(e)
            }

    def predict_oom(self, minutes: int = 5) -> Dict[str, Any]:
        """
        Predict if Out-Of-Memory (OOM) will occur within X minutes.
        Uses linear regression on recent memory usage.
        """
        if len(self.system_history) < 10:
            return {"risk": "unknown", "confidence": 0.0}

        # Use last 20 data points
        recent = self.system_history[-20:]
        timestamps = [x["timestamp"] for x in recent]
        memory_usage = [x["memory_percent"] for x in recent]
        
        # Simple Linear Regression: y = mx + b
        n = len(recent)
        sum_x = sum(timestamps)
        sum_y = sum(memory_usage)
        sum_xy = sum(t * m for t, m in zip(timestamps, memory_usage))
        sum_xx = sum(t * t for t in timestamps)
        
        denominator = (n * sum_xx - sum_x * sum_x)
        if denominator == 0:
            return {"risk": "low", "slope": 0.0}
            
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        intercept = (sum_y - slope * sum_x) / n
        
        # Predict future memory
        future_time = time.time() + (minutes * 60)
        predicted_mem = slope * future_time + intercept
        
        risk = "low"
        if predicted_mem > 95.0:
            risk = "critical"
        elif predicted_mem > 85.0:
            risk = "high"
        elif predicted_mem > 75.0:
            risk = "medium"
            
        return {
            "risk": risk,
            "current_memory": recent[-1]["memory_percent"],
            "predicted_memory_5min": round(predicted_mem, 2),
            "trend_slope": slope
        }

    def calculate_health_score(self) -> int:
        """
        Calculate overall System Health Score (0-100).
        100 = Perfect, 0 = System Critical
        """
        if not self.system_history:
            return 100
            
        latest = self.system_history[-1]
        cpu = latest["cpu_percent"]
        mem = latest["memory_percent"]
        
        score = 100
        
        # CPU Penalties
        if cpu > 90: score -= 30
        elif cpu > 70: score -= 15
        elif cpu > 50: score -= 5
        
        # Memory Penalties
        if mem > 90: score -= 40 # Memory is more critical than CPU for crash risk
        elif mem > 75: score -= 20
        elif mem > 60: score -= 10
        
        # Error Rates (Placeholder - tracked elsewhere ideally)
        # if errors > threshold: score -= ...
        
        return max(0, score)

    def get_database_stats(self) -> Dict[str, Any]:
        """Get basic database statistics."""
        events = self.db.memory

        # Count event types
        regular_events = []
        fused_events = []

        for event in events:
            if hasattr(event, "fusion_count"):
                fused_events.append(event)
            else:
                regular_events.append(event)

        # Location distribution
        locations = Counter(e.location for e in events)

        # Age distribution
        now = time.time()
        ages = [(now - e.timestamp) / 3600 for e in events]  # Hours

        return {
            "total_events": len(events),
            "regular_events": len(regular_events),
            "fused_events": len(fused_events),
            "unique_locations": len(locations),
            "top_locations": dict(locations.most_common(5)),
            "age_stats": {
                "oldest_hours": max(ages) if ages else 0,
                "newest_hours": min(ages) if ages else 0,
                "average_hours": sum(ages) / len(ages) if ages else 0,
            },
            "cache_size": self.db.cache.size() if hasattr(self.db, "cache") else 0,
        }

    def get_fusion_stats(self) -> Dict[str, Any]:
        """Get Event Fusion statistics."""
        events = self.db.memory

        fused_events = [e for e in events if hasattr(e, "fusion_count")]
        regular_events = [e for e in events if not hasattr(e, "fusion_count")]

        if not fused_events:
            return {
                "enabled": False,
                "total_fused": 0,
                "fusion_rate": 0.0,
                "storage_efficiency": 0.0,
                "events_saved": 0,
            }

        # Calculate metrics
        total_fusions = sum(e.fusion_count for e in fused_events)
        original_count = len(events) + total_fusions - len(fused_events)

        fusion_rate = (len(fused_events) / len(events) * 100) if events else 0
        storage_efficiency = (
            ((original_count - len(events)) / original_count * 100) if original_count > 0 else 0
        )

        # Fusion types distribution
        fusion_types = Counter(e.fusion_type for e in fused_events if hasattr(e, "fusion_type"))

        # Pattern distribution
        patterns = Counter(e.pattern for e in fused_events if hasattr(e, "pattern"))

        # Top fused events
        top_fused = sorted(fused_events, key=lambda e: e.fusion_count, reverse=True)[:5]

        return {
            "enabled": True,
            "total_fused": len(fused_events),
            "total_fusions": total_fusions,
            "fusion_rate": round(fusion_rate, 2),
            "storage_efficiency": round(storage_efficiency, 2),
            "events_saved": original_count - len(events),
            "fusion_types": dict(fusion_types),
            "patterns": dict(patterns),
            "top_fused": [
                {
                    "id": e.id[:8],
                    "fusion_count": e.fusion_count,
                    "pattern": getattr(e, "pattern", "unknown"),
                    "tokens": e.raw_data_anchor[:5],
                    "location": e.location,
                }
                for e in top_fused
            ],
        }

    def get_temporal_stats(self) -> Dict[str, Any]:
        """Get temporal pattern statistics."""
        events = self.db.memory

        if not events:
            return {"no_data": True}

        # Extract temporal metadata
        months = []
        days_of_week = []
        hours = []
        seasons = []

        for event in events:
            if hasattr(event, "temporal_metadata") and event.temporal_metadata:
                meta = event.temporal_metadata
                if "month" in meta:
                    months.append(meta["month"])
                if "day_of_week" in meta:
                    days_of_week.append(meta["day_of_week"])
                if "season" in meta:
                    seasons.append(meta["season"])

            # Extract hour from timestamp
            dt = datetime.fromtimestamp(event.timestamp)
            hours.append(dt.hour)

        return {
            "month_distribution": dict(Counter(months)),
            "day_of_week_distribution": dict(Counter(days_of_week)),
            "hour_distribution": dict(Counter(hours)),
            "season_distribution": dict(Counter(seasons)),
            "peak_hour": Counter(hours).most_common(1)[0][0] if hours else None,
            "peak_month": Counter(months).most_common(1)[0][0] if months else None,
        }

    def get_token_stats(self) -> Dict[str, Any]:
        """Get token analysis statistics."""
        events = self.db.memory

        all_tokens = []
        token_counts = []

        for event in events:
            tokens = event.raw_data_anchor
            all_tokens.extend(tokens)
            token_counts.append(len(tokens))

        token_freq = Counter(all_tokens)

        return {
            "total_tokens": len(all_tokens),
            "unique_tokens": len(set(all_tokens)),
            "vocabulary_size": len(token_freq),
            "avg_tokens_per_event": sum(token_counts) / len(token_counts) if token_counts else 0,
            "top_tokens": dict(token_freq.most_common(20)),
            "token_diversity": len(set(all_tokens)) / len(all_tokens) if all_tokens else 0,
        }

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance metrics."""
        return {
            "total_queries": len(self.query_times),
            "avg_query_time_ms": (
                sum(self.query_times) / len(self.query_times) if self.query_times else 0
            ),
            "min_query_time_ms": min(self.query_times) if self.query_times else 0,
            "max_query_time_ms": max(self.query_times) if self.query_times else 0,
            "fusion_compression_rate": self._calculate_fusion_compression_rate(),
        }

    def _calculate_fusion_compression_rate(self) -> float:
        """
        Calculate fusion compression rate.
        
        Shows how much data was compressed through fusion:
        - If 1000 events were ingested but only 100 unique events exist (fusion_count sum=900)
        - total_ingested = 100 (unique) + 900 (fused) = 1000
        - Compression rate = (1 - 100/1000) * 100 = 90%
        """
        events = self.db.memory.get_all()
        
        if not events:
            return 0.0
        
        unique_events = len(events)
        # fusion_count represents *additional* events fused into this one
        # So total ingested = current events + all fused events
        fused_sum = sum(getattr(event, 'fusion_count', 0) for event in events)
        total_ingested = unique_events + fused_sum
        
        if total_ingested == 0:
            return 0.0
        
        # Compression rate: percentage of space saved
        compression_rate = (1 - (unique_events / total_ingested)) * 100.0
        
        return round(compression_rate, 2)

    def track_query(self, duration_ms: float):
        """Track query execution time."""
        self.query_times.append(duration_ms)

        # Keep only last N queries
        if len(self.query_times) > ANALYTICS_QUERY_HISTORY_LIMIT:
            self.query_times = self.query_times[-ANALYTICS_QUERY_HISTORY_LIMIT:]

    def track_fusion(self, event_id: str, strategy: str):
        """Track fusion operation."""
        self.fusion_history.append(
            {"timestamp": time.time(), "event_id": event_id, "strategy": strategy}
        )

        # Keep only last N fusions
        if len(self.fusion_history) > ANALYTICS_FUSION_HISTORY_LIMIT:
            self.fusion_history = self.fusion_history[-ANALYTICS_FUSION_HISTORY_LIMIT:]

    def track_cognitive_state(self, load: float, resonance: float):
        """Track cognitive metrics."""
        # Update Prometheus
        COGNITIVE_LOAD.set(load)
        MEMORY_RESONANCE.set(resonance)
        
        # Track history
        self.cognitive_history.append({
            "timestamp": time.time(),
            "load": load,
            "resonance": resonance
        })
        if len(self.cognitive_history) > ANALYTICS_COGNITIVE_HISTORY_LIMIT:
            self.cognitive_history = self.cognitive_history[-ANALYTICS_COGNITIVE_HISTORY_LIMIT:]

    def get_cognitive_stats(self) -> Dict[str, Any]:
        """Get cognitive state statistics."""
        if not self.cognitive_history:
            return {"avg_load": 0.0, "avg_resonance": 0.0}
            
        recent = self.cognitive_history[-50:] # Last 50 ops
        avg_load = sum(h["load"] for h in recent) / len(recent)
        avg_res = sum(h["resonance"] for h in recent) / len(recent)
        
        return {
            "avg_load": round(avg_load, 2),
            "avg_resonance": round(avg_res, 2),
            "current_load": self.cognitive_history[-1]["load"],
            "current_resonance": self.cognitive_history[-1]["resonance"]
        }

    def generate_report(self, format: str = "text") -> str:
        """
        Generate comprehensive analytics report.

        Args:
            format: "text" or "json"

        Returns:
            Formatted report string
        """
        overview = self.get_overview()

        if format == "json":
            import json

            return json.dumps(overview, indent=2)

        # Text format
        report = []
        report.append("=" * 70)
        report.append("INDB Analytics Report")
        report.append("=" * 70)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # Database Stats
        db_stats = overview["database"]
        report.append("📊 Database Statistics")
        report.append("-" * 70)
        report.append(f"Total Events: {db_stats['total_events']}")
        report.append(f"Regular Events: {db_stats['regular_events']}")
        report.append(f"Fused Events: {db_stats['fused_events']}")
        report.append(f"Unique Locations: {db_stats['unique_locations']}")
        report.append(f"Cache Size: {db_stats['cache_size']}")
        report.append("")

        # Fusion Stats
        fusion_stats = overview["fusion"]
        if fusion_stats.get("enabled"):
            report.append("🔄 Fusion Statistics")
            report.append("-" * 70)
            report.append(f"Fusion Rate: {fusion_stats['fusion_rate']}%")
            report.append(f"Storage Efficiency: {fusion_stats['storage_efficiency']}%")
            report.append(f"Events Saved: {fusion_stats['events_saved']}")
            report.append(f"Total Fusions: {fusion_stats['total_fusions']}")
            report.append("")

        # Token Stats
        token_stats = overview["tokens"]
        report.append("🏷️  Token Analysis")
        report.append("-" * 70)
        report.append(f"Total Tokens: {token_stats['total_tokens']}")
        report.append(f"Unique Tokens: {token_stats['unique_tokens']}")
        report.append(f"Vocabulary Size: {token_stats['vocabulary_size']}")
        report.append(f"Avg Tokens/Event: {token_stats['avg_tokens_per_event']:.2f}")
        report.append("")

        # Top Tokens
        if token_stats["top_tokens"]:
            report.append("Top 10 Tokens:")
            for token, count in list(token_stats["top_tokens"].items())[:10]:
                report.append(f"  {token}: {count}")
            report.append("")

        # Performance
        perf_stats = overview["performance"]
        if perf_stats["total_queries"] > 0:
            report.append("⚡ Performance Metrics")
            report.append("-" * 70)
            report.append(f"Total Queries: {perf_stats['total_queries']}")
            report.append(f"Avg Query Time: {perf_stats['avg_query_time_ms']:.2f}ms")
            report.append(f"Min Query Time: {perf_stats['min_query_time_ms']:.2f}ms")
            report.append(f"Max Query Time: {perf_stats['max_query_time_ms']:.2f}ms")
            report.append("")

        report.append("=" * 70)

        return "\n".join(report)

    def get_insights(self) -> List[str]:
        """
        Generate actionable insights based on analytics.

        Returns:
            List of insight strings
        """
        insights = []
        overview = self.get_overview()

        # Fusion insights
        fusion = overview["fusion"]
        if fusion.get("enabled"):
            if fusion["fusion_rate"] > 70:
                insights.append(
                    f"✅ High fusion rate ({fusion['fusion_rate']}%) - excellent storage efficiency"
                )
            elif fusion["fusion_rate"] < 30:
                insights.append(
                    f"⚠️  Low fusion rate ({fusion['fusion_rate']}%) - consider adjusting similarity threshold"
                )

            if fusion["storage_efficiency"] > 50:
                insights.append(
                    f"💾 Saving {fusion['events_saved']} events through fusion ({fusion['storage_efficiency']}% efficiency)"
                )

        # Token insights
        tokens = overview["tokens"]
        if tokens["token_diversity"] < 0.3:
            insights.append(
                f"⚠️  Low token diversity ({tokens['token_diversity']:.2%}) - events are very similar"
            )
        elif tokens["token_diversity"] > 0.7:
            insights.append(
                f"✅ High token diversity ({tokens['token_diversity']:.2%}) - rich vocabulary"
            )

        # Database size insights
        db = overview["database"]
        if db["total_events"] > ANALYTICS_INSIGHT_EVENT_THRESHOLD:
            insights.append(
                f"📈 Large database ({db['total_events']} events) - consider archiving old data"
            )

        # Performance insights
        perf = overview["performance"]
        if perf["total_queries"] > 0:
            if perf["avg_query_time_ms"] < ANALYTICS_INSIGHT_LATENCY_GOOD_MS:
                insights.append(
                    f"⚡ Excellent query performance ({perf['avg_query_time_ms']:.2f}ms average)"
                )
            elif perf["avg_query_time_ms"] > ANALYTICS_INSIGHT_LATENCY_WARN_MS:
                insights.append(
                    f"⚠️  Slow queries ({perf['avg_query_time_ms']:.2f}ms average) - consider optimization"
                )

        return insights
