"""
Event Fusion Engine for INDB

Intelligent event merging with semantic similarity.
"""

import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
from core.event import Event
from core.constants import (
    FUSION_MAX_FUSION_COUNT,
    FUSION_DEFAULT_THRESHOLD,
    FUSION_FULL_MERGE_THRESHOLD,
    FUSION_SEMANTIC_LINK_THRESHOLD,
    FUSION_W_SEMANTIC,
    FUSION_W_LOCATION_NEURAL,
    FUSION_W_TEMPORAL_NEURAL,
    FUSION_W_TOKEN,
    FUSION_W_LOCATION_HEURISTIC,
    FUSION_W_TEMPORAL_HEURISTIC,
    FUSION_AUTOTUNE_CPU_HIGH,
    FUSION_AUTOTUNE_MEM_HIGH,
    FUSION_AUTOTUNE_CPU_LOW,
    FUSION_AUTOTUNE_STEP,
    FUSION_AUTOTUNE_NORMALIZE_STEP,
    FUSION_INTERVAL_HOUR,
    FUSION_INTERVAL_DAY,
    FUSION_INTERVAL_WEEK,
    FUSION_BURST_MIN_OCCURRENCES,
)

try:
    from services.ml.embeddings import SemanticEmbeddings
    from services.ml.pattern_recognition import PatternRecognizer
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

# Import Penalty Engine
from services.fusion.penalty import PenaltyEngine, PenaltyConfig


@dataclass
class FusedEvent:
    """
    Composite event created from multiple similar events.
    
    Enriched with fusion metadata for deeper interpretations.
    """
    # Core Event fields
    id: str
    timestamp: float
    raw_data_anchor: List[str]
    location: str
    ttl: Optional[int] = None
    temporal_metadata: Dict[str, Any] = field(default_factory=dict)
    blind_payload: Optional[str] = None
    
    # Fusion-specific fields
    fusion_count: int = 1
    fusion_type: str = "original"  # "full_merge", "weighted_merge", "semantic_link"
    source_events: List[str] = field(default_factory=list)
    similarity_score: float = 1.0
    
    # Token enrichment
    token_weights: Dict[str, float] = field(default_factory=dict)
    token_frequency: Dict[str, int] = field(default_factory=dict)
    
    # Temporal enrichment
    temporal_span: Dict[str, Any] = field(default_factory=lambda: {
        "first": None,
        "last": None,
        "occurrences": 1,
        "pattern": "one-time"
    })
    
    # Spatial enrichment
    location_variants: List[str] = field(default_factory=list)
    
    # Related events (for semantic links)
    related_events: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/serialization"""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "raw_data_anchor": self.raw_data_anchor,
            "location": self.location,
            "ttl": self.ttl,
            "temporal_metadata": self.temporal_metadata,
            "blind_payload": self.blind_payload,
            "fusion_count": self.fusion_count,
            "fusion_type": self.fusion_type,
            "source_events": self.source_events,
            "similarity_score": self.similarity_score,
            "token_weights": self.token_weights,
            "token_frequency": self.token_frequency,
            "temporal_span": self.temporal_span,
            "location_variants": self.location_variants,
            "related_events": self.related_events,
            "_type": "FusedEvent"
        }
    
    @staticmethod
    def from_dict(d: Dict[str, Any]) -> 'FusedEvent':
        """Create FusedEvent from dictionary"""
        return FusedEvent(
            id=d.get("id"),
            timestamp=d.get("timestamp"),
            raw_data_anchor=d.get("raw_data_anchor", []),
            location=d.get("location", "Unknown"),
            ttl=d.get("ttl"),
            temporal_metadata=d.get("temporal_metadata", {}),
            blind_payload=d.get("blind_payload"),
            fusion_count=d.get("fusion_count", 1),
            fusion_type=d.get("fusion_type", "original"),
            source_events=d.get("source_events", []),
            similarity_score=d.get("similarity_score", 1.0),
            token_weights=d.get("token_weights", {}),
            token_frequency=d.get("token_frequency", {}),
            temporal_span=d.get("temporal_span", {}),
            location_variants=d.get("location_variants", []),
            related_events=d.get("related_events", [])
        )

class EventFusion:
    """
    Event Fusion Engine
    
    Handles similarity detection and event merging strategies.
    Now using Neural Semantic Embeddings (v3.0).
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize fusion engine
        
        Args:
            config: Fusion configuration
        """
        self.config = config or {
            "enabled": True,
            "threshold": FUSION_DEFAULT_THRESHOLD,
            "strategy": "auto",
            "max_fusion_count": FUSION_MAX_FUSION_COUNT,
            "pattern_detection": True,
            "token_weighting": True
        }
        
        self.embeddings = None
        self.pattern_recognizer = None
        if ML_AVAILABLE:
            try:
                self.embeddings = SemanticEmbeddings()
                self.pattern_recognizer = PatternRecognizer()
                print("Neural Fusion: ENABLED (Sentence Transformers + DBSCAN)")
            except Exception as e:
                print(f"Neural Fusion: DISABLED ({e})")
        
        # Initialize Penalty Engine
        self.penalty_engine = PenaltyEngine(PenaltyConfig())
        print("Penalty System: ENABLED (Frequency, Isolation, Context Gap)")
    
    def detect_global_patterns(self, events: List[Any]) -> Dict[str, Any]:
        """
        Detect patterns across a list of events using DBSCAN.
        """
        if self.pattern_recognizer:
            return self.pattern_recognizer.detect_patterns(events)
        return {"error": "Pattern Recognizer not available"}

    
    def calculate_similarity(self, event1: Any, event2: Any) -> float:
        """
        Calculate semantic similarity between two events.
        
        Args:
            event1: First event
            event2: Second event
            
        Returns:
            Similarity score from 0.0 (different) to 1.0 (identical)
        """
        # Common Spatiotemporal Factors
        # Location similarity
        location_match = 1.0 if event1.location == event2.location else 0.0
        
        # Temporal proximity (events within 1 hour = high proximity)
        time_diff = abs(event1.timestamp - event2.timestamp)
        temporal_proximity = max(0.0, 1.0 - (time_diff / FUSION_INTERVAL_HOUR))
        
        # NEURAL PATH
        if self.embeddings:
            semantic_score = self.embeddings.calculate_similarity(event1.raw_data_anchor, event2.raw_data_anchor)
            # Weighted mix: semantic/location/temporal using named weights
            raw_similarity = (
                semantic_score * FUSION_W_SEMANTIC +
                location_match * FUSION_W_LOCATION_NEURAL +
                temporal_proximity * FUSION_W_TEMPORAL_NEURAL
            )
            
            # Apply Penalty System
            penalty_result = self.penalty_engine.apply(
                event1.raw_data_anchor,
                event2.raw_data_anchor,
                raw_similarity,
                event1.location,
                event2.location
            )
            
            if penalty_result.decision == "drop":
                return 0.0
            
            return round(penalty_result.final_score, 3)

        # HEURISTIC PATH (Fallback)
        # Extract tokens
        tokens1 = set(event1.raw_data_anchor)
        tokens2 = set(event2.raw_data_anchor)
        
        # Jaccard similarity for tokens
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        
        token_similarity = len(intersection) / len(union) if union else 0.0
        
        # Location similarity
        location_match = 1.0 if event1.location == event2.location else 0.0
        
        # Temporal proximity (events within 1 hour = high proximity)
        time_diff = abs(event1.timestamp - event2.timestamp)
        temporal_proximity = max(0.0, 1.0 - (time_diff / FUSION_INTERVAL_HOUR))
        
        # Weighted combination
        raw_similarity = (
            token_similarity * FUSION_W_TOKEN +
            location_match * FUSION_W_LOCATION_HEURISTIC +
            temporal_proximity * FUSION_W_TEMPORAL_HEURISTIC
        )
        
        # Apply Penalty System
        penalty_result = self.penalty_engine.apply(
            event1.raw_data_anchor,
            event2.raw_data_anchor,
            raw_similarity,
            event1.location,
            event2.location
        )
        
        # DEBUG PRINT
        print(f"DEBUG: Sim Calc. Raw={raw_similarity:.3f} Final={penalty_result.final_score:.3f} Decision={penalty_result.decision}")
        
        if penalty_result.decision == "drop":
            return 0.0
        
        return round(penalty_result.final_score, 3)
    
    def full_merge(self, base: Any, new: Any) -> FusedEvent:
        """
        Full merge strategy for nearly identical events.
        
        Args:
            base: Base event (existing)
            new: New event to merge
            
        Returns:
            Fused event with combined data
        """
        # Combine tokens (unique)
        combined_tokens = list(set(base.raw_data_anchor + new.raw_data_anchor))
        
        # Calculate token frequencies
        token_freq = {}
        for token in base.raw_data_anchor:
            token_freq[token] = token_freq.get(token, 0) + 1
        for token in new.raw_data_anchor:
            token_freq[token] = token_freq.get(token, 0) + 1
        
        # Get existing fusion count
        base_count = base.fusion_count if isinstance(base, FusedEvent) else 1
        base_sources = base.source_events if isinstance(base, FusedEvent) else [base.id]
        
        # Create fused event
        fused = FusedEvent(
            id=base.id,
            timestamp=min(base.timestamp, new.timestamp),  # Keep earliest
            raw_data_anchor=combined_tokens,
            location=base.location,
            ttl=base.ttl,
            temporal_metadata=base.temporal_metadata,
            blind_payload=getattr(base, "blind_payload", None) or getattr(new, "blind_payload", None),
            
            fusion_count=base_count + 1,
            fusion_type="full_merge",
            source_events=base_sources + [new.id],
            similarity_score=self.calculate_similarity(base, new),
            
            token_frequency=token_freq,
            
            temporal_span={
                "first": min(base.timestamp, new.timestamp),
                "last": max(base.timestamp, new.timestamp),
                "occurrences": base_count + 1,
                "pattern": self._detect_pattern(base_count + 1, 
                                               max(base.timestamp, new.timestamp) - min(base.timestamp, new.timestamp))
            }
        )
        
        # Calculate token weights
        fused.token_weights = {
            token: freq / fused.fusion_count 
            for token, freq in token_freq.items()
        }
        
        return fused
    
    def weighted_merge(self, base: Any, new: Any, similarity: float) -> FusedEvent:
        """
        Weighted merge strategy for similar events.
        
        Args:
            base: Base event
            new: New event
            similarity: Similarity score
            
        Returns:
            Fused event with weighted tokens
        """
        # Calculate token weights
        token_weights = {}
        
        # Base event tokens get full weight
        for token in base.raw_data_anchor:
            token_weights[token] = token_weights.get(token, 0.0) + 1.0
        
        # New event tokens get weight based on similarity
        for token in new.raw_data_anchor:
            token_weights[token] = token_weights.get(token, 0.0) + similarity
        
        # Sort tokens by weight
        sorted_tokens = sorted(
            token_weights.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        base_count = base.fusion_count if isinstance(base, FusedEvent) else 1
        base_sources = base.source_events if isinstance(base, FusedEvent) else [base.id]
        
        fused = FusedEvent(
            id=base.id,
            timestamp=base.timestamp,
            raw_data_anchor=[t[0] for t in sorted_tokens],
            location=base.location,
            ttl=base.ttl,
            temporal_metadata=base.temporal_metadata,
            blind_payload=getattr(base, "blind_payload", None) or getattr(new, "blind_payload", None),
            
            fusion_count=base_count + 1,
            fusion_type="weighted_merge",
            source_events=base_sources + [new.id],
            similarity_score=similarity,
            
            token_weights=dict(sorted_tokens),
            
            temporal_span={
                "first": min(base.timestamp, new.timestamp),
                "last": max(base.timestamp, new.timestamp),
                "occurrences": base_count + 1,
                "pattern": self._detect_pattern(base_count + 1,
                                               max(base.timestamp, new.timestamp) - min(base.timestamp, new.timestamp))
            }
        )
        
        return fused
    
    def semantic_link(self, base: Any, new: Any, similarity: float) -> Tuple[Any, Any]:
        """
        Semantic link strategy - keep separate but link events.
        
        Args:
            base: Base event
            new: New event
            similarity: Similarity score
            
        Returns:
            Tuple of (updated base, new event)
        """
        # Calculate shared tokens
        shared_tokens = list(set(base.raw_data_anchor) & set(new.raw_data_anchor))
        
        # Add link to base event
        if isinstance(base, FusedEvent):
            base.related_events.append({
                "id": new.id,
                "similarity": similarity,
                "relationship": "semantic_variant",
                "shared_tokens": shared_tokens,
                "timestamp": new.timestamp
            })
        
        return base, new
    
    def _detect_pattern(self, occurrences: int, duration: float) -> str:
        """
        Detect temporal pattern from fusion data.
        
        Args:
            occurrences: Number of occurrences
            duration: Time span in seconds
            
        Returns:
            Pattern type
        """
        if occurrences == 1:
            return "one-time"
        
        # Burst: multiple occurrences in short time
        if duration < FUSION_INTERVAL_HOUR and occurrences > FUSION_BURST_MIN_OCCURRENCES:
            return "burst"
        
        # Calculate average interval
        avg_interval = duration / (occurrences - 1) if occurrences > 1 else 0
        
        # Recurring patterns
        if FUSION_INTERVAL_HOUR < avg_interval < FUSION_INTERVAL_DAY:
            return "daily_recurring"
        elif FUSION_INTERVAL_DAY < avg_interval < FUSION_INTERVAL_WEEK:
            return "weekly_recurring"
        elif avg_interval >= FUSION_INTERVAL_WEEK:
            return "monthly_recurring"
        
        return "irregular_recurring"
    
    def find_similar_events(
        self,
        target: Any,
        event_pool: List[Any],
        threshold: float = 0.5,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find events similar to target.
        
        Args:
            target: Target event
            event_pool: Pool of events to search
            threshold: Minimum similarity threshold
            max_results: Maximum number of results
            
        Returns:
            List of similar events with metadata
        """
        similarities = []
        
        for event in event_pool:
            # Skip if target is already part of this fusion
            if isinstance(event, FusedEvent) and target.id in event.source_events:
                continue
            
            # Skip self
            if event.id == target.id:
                continue
            
            similarity = self.calculate_similarity(target, event)
            
            if similarity >= threshold:
                similarities.append({
                    "id": event.id,
                    "similarity": similarity,
                    "event": event
                })
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        
        return similarities[:max_results]
    
    def should_fuse(self, similarity: float) -> Tuple[bool, str]:
        """
        Determine if events should be fused and which strategy to use.
        
        Args:
            similarity: Similarity score
            
        Returns:
            Tuple of (should_fuse, strategy)
        """
        if not self.config["enabled"]:
            return False, "disabled"
        
        if similarity > FUSION_FULL_MERGE_THRESHOLD:
            return True, "full_merge"

        # Use dynamic threshold from config (tuned by tune_threshold)
        if similarity >= self.config["threshold"]:
            return True, "weighted_merge"

        if similarity >= FUSION_SEMANTIC_LINK_THRESHOLD:
            # Semantic link only
            return False, "semantic_link"

        return False, "none"

    def tune_threshold(self, metrics: Dict[str, Any]) -> float:
        """
        Auto-tune fusion threshold based on system health.
        
        Logic:
        - High CPU (>80%): Increase threshold (Strict fusion to save CPU)
        - High Memory (>80%) & Low CPU (<50%): Decrease threshold (Aggressive fusion to save RAM)
        - Otherwise: Normalize towards default
        
        Args:
            metrics: System health metrics from INDBAnalytics
            
        Returns:
            New threshold value
        """
        cpu_load = metrics.get("cpu_percent", 0)
        mem_load = metrics.get("memory_percent", 0)
        default_threshold = FUSION_DEFAULT_THRESHOLD

        current_threshold = self.config["threshold"]
        new_threshold = current_threshold

        if cpu_load > FUSION_AUTOTUNE_CPU_HIGH:
            # CPU bottleneck: Reduce fusion overhead by being stricter
            new_threshold = min(FUSION_FULL_MERGE_THRESHOLD, current_threshold + FUSION_AUTOTUNE_STEP)
        elif mem_load > FUSION_AUTOTUNE_MEM_HIGH and cpu_load < FUSION_AUTOTUNE_CPU_LOW:
            # Memory constrained: Fuse aggressively (more merges = fewer events)
            new_threshold = max(FUSION_SEMANTIC_LINK_THRESHOLD, current_threshold - FUSION_AUTOTUNE_STEP)
        else:
            # Normalize towards default
            if current_threshold > default_threshold:
                new_threshold = max(default_threshold, current_threshold - FUSION_AUTOTUNE_NORMALIZE_STEP)
            elif current_threshold < default_threshold:
                new_threshold = min(default_threshold, current_threshold + FUSION_AUTOTUNE_NORMALIZE_STEP)

        self.config["threshold"] = round(new_threshold, 3)
        return self.config["threshold"]
    
    def fuse_events(
        self,
        base: Any,
        new: Any,
        strategy: Optional[str] = None
    ) -> Union[FusedEvent, Tuple[Any, Any]]:
        """
        Fuse two events using specified or auto-detected strategy.
        
        Args:
            base: Base event
            new: New event
            strategy: Fusion strategy (auto-detected if None)
            
        Returns:
            Fused event or tuple of linked events
        """
        similarity = self.calculate_similarity(base, new)
        
        if strategy is None:
            should_fuse, strategy = self.should_fuse(similarity)
            if not should_fuse:
                return new  # Return new event unchanged
        
        if strategy == "full_merge":
            return self.full_merge(base, new)
        elif strategy == "weighted_merge":
            return self.weighted_merge(base, new, similarity)
        elif strategy == "semantic_link":
            return self.semantic_link(base, new, similarity)
        else:
            return new
