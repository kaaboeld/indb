"""
Associative Memory for INDB
Finds related events based on token similarity (like human memory associations)
"""

from typing import List, Dict, Any, Set
import math

def jaccard_similarity(set1: Set[str], set2: Set[str]) -> float:
    """
    Calculate Jaccard similarity between two sets
    
    Jaccard = |A ∩ B| / |A ∪ B|
    
    Returns value between 0.0 (no overlap) and 1.0 (identical)
    """
    if not set1 or not set2:
        return 0.0
    
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    
    return intersection / union if union > 0 else 0.0

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors
    
    Returns value between -1.0 and 1.0
    """
    if len(vec1) != len(vec2):
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return dot_product / (magnitude1 * magnitude2)

class AssociativeMemory:
    """
    Finds related events based on token similarity
    
    Mimics how human memory works - one memory triggers related memories
    """
    
    def __init__(self, similarity_threshold: float = 0.3):
        """
        Initialize Associative Memory
        
        Args:
            similarity_threshold: Minimum similarity to consider events related (0.0-1.0)
        """
        self.similarity_threshold = similarity_threshold
    
    def find_associations(
        self,
        source_event: Dict[str, Any],
        candidate_events: List[Dict[str, Any]],
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find events associated with source event
        
        Args:
            source_event: The event to find associations for
            candidate_events: Pool of events to search
            max_results: Maximum number of associations to return
        
        Returns:
            List of associated events with similarity scores
        """
        source_tokens = set(source_event.get("interpretation", {}).get("tokens", []))
        source_id = source_event.get("id")
        
        if not source_tokens:
            return []
        
        associations = []
        
        for candidate in candidate_events:
            # Skip self
            if candidate.get("id") == source_id:
                continue
            
            candidate_tokens = set(candidate.get("interpretation", {}).get("tokens", []))
            
            if not candidate_tokens:
                continue
            
            # Calculate similarity
            similarity = jaccard_similarity(source_tokens, candidate_tokens)
            
            if similarity >= self.similarity_threshold:
                associations.append({
                    "event": candidate,
                    "similarity": similarity,
                    "shared_tokens": list(source_tokens & candidate_tokens),
                    "association_strength": self._calculate_strength(similarity)
                })
        
        # Sort by similarity (strongest first)
        associations.sort(key=lambda x: x["similarity"], reverse=True)
        
        return associations[:max_results]
    
    def _calculate_strength(self, similarity: float) -> str:
        """
        Convert similarity score to human-readable strength
        
        Args:
            similarity: Jaccard similarity (0.0-1.0)
        
        Returns:
            Strength label: "weak", "moderate", "strong", "very_strong"
        """
        if similarity >= 0.7:
            return "very_strong"
        elif similarity >= 0.5:
            return "strong"
        elif similarity >= 0.3:
            return "moderate"
        else:
            return "weak"
    
    def find_temporal_associations(
        self,
        source_event: Dict[str, Any],
        candidate_events: List[Dict[str, Any]],
        time_window_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Find events that occurred near the same time
        
        Args:
            source_event: The event to find temporal associations for
            candidate_events: Pool of events to search
            time_window_hours: Time window in hours
        
        Returns:
            List of temporally associated events
        """
        # This would require timestamp comparison
        # Implementation depends on Event structure
        # Placeholder for now
        return []
    
    def find_location_associations(
        self,
        source_event: Dict[str, Any],
        candidate_events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Find events from the same location
        
        Args:
            source_event: The event to find location associations for
            candidate_events: Pool of events to search
        
        Returns:
            List of location-associated events
        """
        source_location = source_event.get("original_location")
        
        if not source_location:
            return []
        
        location_events = []
        
        for candidate in candidate_events:
            if candidate.get("id") == source_event.get("id"):
                continue
            
            if candidate.get("original_location") == source_location:
                location_events.append({
                    "event": candidate,
                    "association_type": "location",
                    "location": source_location
                })
        
        return location_events

# Global associative memory instance
default_associative_memory = AssociativeMemory(similarity_threshold=0.3)

def find_related_events(
    source_event: Dict[str, Any],
    all_events: List[Dict[str, Any]],
    max_results: int = 10,
    threshold: float = 0.3
) -> List[Dict[str, Any]]:
    """
    Convenience function to find related events
    
    Args:
        source_event: Event to find associations for
        all_events: All available events
        max_results: Maximum results to return
        threshold: Similarity threshold
    
    Returns:
        List of associated events with metadata
    """
    memory = AssociativeMemory(similarity_threshold=threshold)
    return memory.find_associations(source_event, all_events, max_results)
