"""
Contextual Lens Module for INDB

Implements adaptive data interpretation with adjustable spectrum ratios.
The lens acts as a "Third Half" - a virtual 50% view formed by blending
two contexts (H1 and H2) with configurable weights.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Optional, Callable
from enum import Enum
import time
import random
from core.event import Event

logger = logging.getLogger("indb.lens")


class LensMode(Enum):
    """Lens focusing modes"""
    SHARP_FOCUS = "sharp"      # Narrow, detailed focus
    DEEP_FOCUS = "deep"        # Hierarchical depth
    WIDE_ANGLE = "wide"        # Broad overview


@dataclass
class DataContext:
    """
    Represents a data context (H1 or H2)
    A context is a logical grouping of events based on filters
    """
    name: str
    filter_fn: Callable[[Event], bool]
    weight: float = 1.0
    
    # Optional temporal bounds
    time_start: Optional[float] = None
    time_end: Optional[float] = None
    
    # Optional semantic bounds
    tags: Optional[List[str]] = None
    locations: Optional[List[str]] = None
    
    def matches(self, event: Event) -> bool:
        """Check if event belongs to this context"""
        try:
            return self.filter_fn(event)
        except Exception as e:
            logger.warning("Context filter error: %s", e)
            return False


@dataclass
class ContextualLens:
    """
    Adaptive query lens for INDB
    
    Implements the "Third Half" concept - a virtual 50% view
    formed by blending two contexts with adjustable ratios.
    """
    id: str
    
    # Fixed lens width (The Third Half = 50%)
    width: float = 0.5
    
    # Lens position on spectrum (0.0 to 1.0)
    offset: float = 0.5
    
    # H1/H2 blend ratio (must sum to 1.0)
    # Examples: (0.1, 0.9), (0.3, 0.7), (0.5, 0.5), (0.7, 0.3), (0.9, 0.1)
    ratio: Tuple[float, float] = (0.5, 0.5)
    
    # Lens properties
    mode: LensMode = LensMode.SHARP_FOCUS
    zoom: float = 1.0  # Cognitive zoom (0.1 = child, 10.0 = adult)
    refraction: float = 1.0  # Subjective interpretation weight
    
    # Context sources
    context_a: str = "recent"
    context_b: str = "historical"
    
    def validate_ratio(self):
        """Ensure ratio sums to 1.0"""
        total = sum(self.ratio)
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Ratio must sum to 1.0, got {total}")
    
    def shift_spectrum(self, new_offset: float):
        """Move lens position on spectrum"""
        self.offset = max(0.0, min(1.0, new_offset))
    
    def adjust_ratio(self, h1_weight: float):
        """
        Adjust H1/H2 blend ratio
        
        Args:
            h1_weight: Weight for H1 (0.0 to 1.0)
        """
        h1_weight = max(0.0, min(1.0, h1_weight))
        self.ratio = (h1_weight, 1.0 - h1_weight)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize lens configuration"""
        return {
            "id": self.id,
            "width": self.width,
            "offset": self.offset,
            "ratio": list(self.ratio),
            "mode": self.mode.value,
            "zoom": self.zoom,
            "refraction": self.refraction,
            "context_a": self.context_a,
            "context_b": self.context_b,
        }


class LensQueryEngine:
    """
    Executes queries through Contextual Lens
    
    Renders the "Third Half" by blending two contexts
    with adjustable spectrum ratios.
    """
    
    def __init__(self, indb):
        """
        Initialize lens query engine
        
        Args:
            indb: INDB instance
        """
        self.indb = indb
        self.contexts = self._init_contexts()
    
    def _init_contexts(self) -> Dict[str, DataContext]:
        """Initialize predefined contexts"""
        now = time.time()
        day_ago = now - 86400
        
        return {
            "recent": DataContext(
                name="recent",
                filter_fn=lambda e: e.timestamp >= day_ago,
                time_start=day_ago,
            ),
            "historical": DataContext(
                name="historical",
                filter_fn=lambda e: e.timestamp < day_ago,
                time_end=day_ago,
            ),
            "high_frequency": DataContext(
                name="high_frequency",
                filter_fn=lambda e: len(e.raw_data_anchor) > 5,
            ),
            "simple": DataContext(
                name="simple",
                filter_fn=lambda e: len(e.raw_data_anchor) <= 5,
            ),
            "all": DataContext(
                name="all",
                filter_fn=lambda e: True,
            ),
        }
    
    def render(self, lens: ContextualLens, limit: int = 100) -> Dict[str, Any]:
        """
        Render data through lens (The Third Half)
        
        Args:
            lens: Contextual lens configuration
            limit: Maximum events in lens view
        
        Returns:
            {
                "h1_events": [...],  # Events from context A
                "h2_events": [...],  # Events from context B
                "lens_view": [...],  # Blended "Third Half"
                "metadata": {...}
            }
        """
        lens.validate_ratio()
        
        # Get contexts
        ctx_a = self.contexts.get(lens.context_a)
        ctx_b = self.contexts.get(lens.context_b)
        
        if not ctx_a or not ctx_b:
            raise ValueError(f"Invalid contexts: {lens.context_a}, {lens.context_b}")
        
        # Filter events by context
        h1_events = [e for e in self.indb.memory if ctx_a.matches(e)]
        h2_events = [e for e in self.indb.memory if ctx_b.matches(e)]

        logger.debug(
            "Lens render: H1(%s)=%d events, H2(%s)=%d events",
            lens.context_a, len(h1_events),
            lens.context_b, len(h2_events),
        )
        
        # Apply lens ratio to determine blend
        h1_count = int(limit * lens.ratio[0])
        h2_count = int(limit * lens.ratio[1])
        
        # Apply zoom and mode
        h1_events = self._apply_zoom(h1_events, lens.zoom, lens.mode)
        h2_events = self._apply_zoom(h2_events, lens.zoom, lens.mode)
        
        # Sample from each context based on ratio
        h1_sample = self._weighted_sample(h1_events, h1_count, lens.refraction)
        h2_sample = self._weighted_sample(h2_events, h2_count, lens.refraction)
        
        # Blend into "Third Half"
        lens_view = self._blend_contexts(h1_sample, h2_sample, lens)
        
        return {
            "h1_events": [e.to_dict() for e in h1_sample],
            "h2_events": [e.to_dict() for e in h2_sample],
            "lens_view": [e.to_dict() for e in lens_view],
            "metadata": {
                "h1_weight": lens.ratio[0],
                "h2_weight": lens.ratio[1],
                "h1_count": len(h1_sample),
                "h2_count": len(h2_sample),
                "lens_count": len(lens_view),
                "zoom": lens.zoom,
                "mode": lens.mode.value,
                "offset": lens.offset,
                "total_h1": len(h1_events),
                "total_h2": len(h2_events),
            }
        }
    
    def _apply_zoom(self, events: List[Event], zoom: float, mode: LensMode) -> List[Event]:
        """
        Apply cognitive zoom to events
        
        Args:
            events: Events to zoom
            zoom: Zoom level (0.1 = child, 10.0 = adult)
            mode: Lens mode
        
        Returns:
            Zoomed events
        """
        if mode == LensMode.SHARP_FOCUS:
            # Narrow focus on most recent
            return sorted(events, key=lambda e: e.timestamp, reverse=True)
        elif mode == LensMode.DEEP_FOCUS:
            # Hierarchical depth (could expand fusion chains here)
            return sorted(events, key=lambda e: len(e.raw_data_anchor), reverse=True)
        else:  # WIDE_ANGLE
            # Broad overview (chronological)
            return sorted(events, key=lambda e: e.timestamp)
    
    def _weighted_sample(self, events: List[Event], count: int, refraction: float) -> List[Event]:
        """
        Sample events with subjective weighting
        
        Args:
            events: Events to sample
            count: Number to sample
            refraction: Subjective weight
        
        Returns:
            Sampled events
        """
        if len(events) <= count:
            return events
        
        # Apply refraction (subjective importance)
        weighted = [(e, self._calculate_importance(e, refraction)) for e in events]
        weighted.sort(key=lambda x: x[1], reverse=True)
        
        return [e for e, _ in weighted[:count]]
    
    def _calculate_importance(self, event: Event, refraction: float) -> float:
        """
        Calculate subjective importance score
        
        Args:
            event: Event to score
            refraction: Subjective weight
        
        Returns:
            Importance score
        """
        base_score = 1.0
        
        # Recency bias
        age = time.time() - event.timestamp
        recency = 1.0 / (1.0 + age / 86400)  # Decay over days
        
        # Complexity bias
        complexity = min(len(event.raw_data_anchor) / 10.0, 1.0)
        
        # Apply refraction (user's subjective lens)
        return base_score * (recency ** refraction) * (complexity ** (1.0 - refraction))
    
    def _blend_contexts(self, h1: List[Event], h2: List[Event], lens: ContextualLens) -> List[Event]:
        """
        Blend two contexts into unified "Third Half"
        
        Interleaves events based on ratio and offset
        
        Args:
            h1: Events from context A
            h2: Events from context B
            lens: Lens configuration
        
        Returns:
            Blended events (The Third Half)
        """
        blended = []
        i1, i2 = 0, 0
        
        # Interleave based on ratio
        while i1 < len(h1) or i2 < len(h2):
            # Determine which context to pull from
            if i1 >= len(h1):
                blended.append(h2[i2])
                i2 += 1
            elif i2 >= len(h2):
                blended.append(h1[i1])
                i1 += 1
            else:
                # Use ratio to decide probabilistically
                if random.random() < lens.ratio[0]:
                    blended.append(h1[i1])
                    i1 += 1
                else:
                    blended.append(h2[i2])
                    i2 += 1
        
        # Limit to lens width (50% of total)
        lens_limit = int(len(blended) * lens.width)
        return blended[:lens_limit]
