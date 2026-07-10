"""
Event model for INDB

Represents an abstract sensory event without pre-assigned meaning.
"""

import time
import uuid
from typing import List, Dict, Any, Optional


class Event:
    """
    Abstract Event - stores raw sensory data without interpretation.

    Attributes:
        id: Unique event identifier
        timestamp: Unix timestamp of event creation
        raw_data_anchor: List of abstract sensory tokens
        location: Physical/virtual location
        ttl: Time to live in seconds (optional)
        temporal_metadata: Metadata for temporal filtering
    """

    def __init__(
        self,
        raw_data_anchor: List[str],
        location: str,
        id: Optional[str] = None,
        timestamp: Optional[float] = None,
        ttl: Optional[int] = None,
        temporal_metadata: Optional[Dict[str, Any]] = None,
        blind_payload: Optional[str] = None,
        binary_payload: Optional[bytes] = None,
        source_id: Optional[str] = None,
        fusion_count: int = 0,
        is_fused: bool = False,
    ):
        self.id = id if id else str(uuid.uuid4())
        self.timestamp = timestamp if timestamp else time.time()
        self.raw_data_anchor = raw_data_anchor
        self.location = location
        self.ttl = ttl
        self.temporal_metadata = temporal_metadata or {}
        self.blind_payload = blind_payload
        self.binary_payload = binary_payload
        self.source_id = source_id
        self.fusion_count = fusion_count
        self.is_fused = is_fused

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert event to dictionary for serialization.
        Note: binary_payload is excluded from standard dict/JSON serialization 
        unless handled explicitly by the caller, to prevent JSON errors.
        """
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "raw_data_anchor": self.raw_data_anchor,
            "location": self.location,
            "ttl": self.ttl,
            "temporal_metadata": self.temporal_metadata,
            "blind_payload": self.blind_payload,
            # "binary_payload": self.binary_payload, # Excluded for JSON safety
            "source_id": self.source_id,
            "fusion_count": self.fusion_count,
            "is_fused": self.is_fused,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Event":
        """Create event from dictionary."""
        location = d.get("location")
        blind_payload = d.get("blind_payload")
        if blind_payload is not None and not (location and str(location).strip()):
            raise ValueError(
                "Black Box Contract violation: blind_payload requires a non-empty location."
            )
        return Event(
            raw_data_anchor=d.get("raw_data_anchor", []),
            location=location or "unknown",
            id=d.get("id"),
            timestamp=d.get("timestamp"),
            ttl=d.get("ttl"),
            temporal_metadata=d.get("temporal_metadata", {}),
            blind_payload=d.get("blind_payload"),
            # binary_payload is typically not in the dict unless manually injected
            binary_payload=d.get("binary_payload"),
            source_id=d.get("source_id"),
            fusion_count=d.get("fusion_count", 0),
            is_fused=d.get("is_fused", False),
        )

    def __repr__(self) -> str:
        return (
            f"Event(id={self.id[:8]}, tokens={len(self.raw_data_anchor)}, location={self.location})"
        )
