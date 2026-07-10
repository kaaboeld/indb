"""
Pattern Recognition Service for INDB

ML-based pattern detection using DBSCAN clustering.
Replaces rule-based pattern detection with intelligent clustering.
"""

from typing import List, Dict, Any, Optional
import numpy as np
from datetime import datetime
from collections import defaultdict

try:
    from sklearn.cluster import DBSCAN
    from sklearn.preprocessing import StandardScaler
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False


class PatternRecognizer:
    """
    ML-based pattern recognition for event sequences.
    
    Uses DBSCAN clustering to automatically detect:
    - Burst patterns (rapid sequences)
    - Recurring patterns (regular intervals)
    - Anomalies (outliers)
    """
    
    def __init__(self, eps: float = 0.3, min_samples: int = 2):
        """
        Initialize pattern recognizer.
        
        Args:
            eps: Maximum distance between samples in a cluster
            min_samples: Minimum samples in a cluster
        """
        if not ML_AVAILABLE:
            raise ImportError("scikit-learn required for PatternRecognizer")
        
        self.scaler = StandardScaler()
        self.clusterer = DBSCAN(eps=eps, min_samples=min_samples)
        self.patterns_cache = {}
    
    def detect_patterns(self, events: List[Any]) -> Dict[str, Any]:
        """
        Detect patterns in event sequence.
        
        Args:
            events: List of Event objects
            
        Returns:
            Dictionary with pattern analysis
        """
        if len(events) < 2:
            return {"patterns": {}, "clusters": 0, "anomalies": 0}
        
        # Extract features
        features = self._extract_features(events)
        
        # Normalize
        features_scaled = self.scaler.fit_transform(features)
        
        # Cluster
        labels = self.clusterer.fit_predict(features_scaled)
        
        # Analyze clusters
        analysis = self._analyze_clusters(events, labels)
        
        return analysis
    
    def _extract_features(self, events: List[Any]) -> np.ndarray:
        """
        Extract numerical features from events.
        
        Features:
        - Time delta from first event (normalized)
        - Token count
        - Token diversity (unique tokens / total tokens)
        - Hour of day
        - Day of week
        """
        if not events:
            return np.array([])
        
        features = []
        first_timestamp = events[0].timestamp
        
        for event in events:
            # Temporal features
            time_delta = (event.timestamp - first_timestamp) / 3600  # Hours
            dt = datetime.fromtimestamp(event.timestamp)
            hour = dt.hour
            day_of_week = dt.weekday()
            
            # Token features
            token_count = len(event.raw_data_anchor)
            unique_tokens = len(set(event.raw_data_anchor))
            token_diversity = unique_tokens / token_count if token_count > 0 else 0
            
            features.append([
                time_delta,
                token_count,
                token_diversity,
                hour,
                day_of_week
            ])
        
        return np.array(features)
    
    def _analyze_clusters(self, events: List[Any], labels: np.ndarray) -> Dict[str, Any]:
        """
        Analyze clustering results.
        
        Args:
            events: Original events
            labels: Cluster labels from DBSCAN
            
        Returns:
            Pattern analysis dictionary
        """
        clusters = defaultdict(list)
        anomalies = []
        
        # Group events by cluster
        for event, label in zip(events, labels):
            if label == -1:  # Anomaly
                anomalies.append(event.id)
            else:
                clusters[label].append(event)
        
        # Analyze each cluster
        patterns = {}
        for cluster_id, cluster_events in clusters.items():
            pattern_type = self._classify_cluster_pattern(cluster_events)
            patterns[f"cluster_{cluster_id}"] = {
                "type": pattern_type,
                "event_count": len(cluster_events),
                "events": [e.id for e in cluster_events],
                "avg_interval": self._calculate_avg_interval(cluster_events)
            }
        
        return {
            "patterns": patterns,
            "clusters": len(clusters),
            "anomalies": len(anomalies),
            "anomaly_ids": anomalies,
            "total_events": len(events)
        }
    
    def _classify_cluster_pattern(self, events: List[Any]) -> str:
        """
        Classify pattern type for a cluster.
        
        Args:
            events: Events in cluster
            
        Returns:
            Pattern type string
        """
        if len(events) < 2:
            return "one-time"
        
        # Calculate time intervals
        intervals = []
        sorted_events = sorted(events, key=lambda e: e.timestamp)
        for i in range(1, len(sorted_events)):
            interval = sorted_events[i].timestamp - sorted_events[i-1].timestamp
            intervals.append(interval)
        
        avg_interval = np.mean(intervals)
        std_interval = np.std(intervals)
        
        # Classify based on intervals
        if avg_interval < 3600:  # < 1 hour
            return "burst"
        elif 3600 <= avg_interval < 86400:  # 1-24 hours
            if std_interval / avg_interval < 0.3:  # Low variance
                return "daily_recurring"
            else:
                return "irregular_recurring"
        elif 86400 <= avg_interval < 604800:  # 1-7 days
            return "weekly_recurring"
        else:
            return "monthly_recurring"
    
    def _calculate_avg_interval(self, events: List[Any]) -> float:
        """Calculate average time interval between events."""
        if len(events) < 2:
            return 0.0
        
        sorted_events = sorted(events, key=lambda e: e.timestamp)
        intervals = [
            sorted_events[i].timestamp - sorted_events[i-1].timestamp
            for i in range(1, len(sorted_events))
        ]
        return float(np.mean(intervals)) if intervals else 0.0
    
    def predict_next_occurrence(self, events: List[Any]) -> Optional[float]:
        """
        Predict timestamp of next occurrence.
        
        Args:
            events: Historical events
            
        Returns:
            Predicted timestamp or None
        """
        if len(events) < 2:
            return None
        
        avg_interval = self._calculate_avg_interval(events)
        if avg_interval == 0:
            return None
        
        last_event = max(events, key=lambda e: e.timestamp)
        return last_event.timestamp + avg_interval
