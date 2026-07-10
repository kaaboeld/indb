"""
INDB API Models (v2)

Centralized Pydantic models for request/response schemas.
Input → Output axiom: defaults from constants, no hardcoding.
"""
import time
from typing import List, Dict, Any, Optional, Generic, TypeVar
from pydantic import BaseModel, Field, model_validator

from core.constants import (
    INTERPRET_FIREWALL_MODE_DEFAULT,
    INTERPRET_LIMIT_DEFAULT,
)


T = TypeVar("T")


class StandardResponse(BaseModel, Generic[T]):
    """Standardized API Response Envelope"""
    data: T
    meta: Optional[Dict[str, Any]] = None
    status: str = "success"
    timestamp: float = Field(default_factory=time.time)


class EventCreate(BaseModel):
    """Request model for creating events."""
    raw_data_anchor: List[str]
    location: str
    ttl: Optional[int] = None
    timestamp: Optional[float] = Field(default_factory=time.time)
    blind_payload: Optional[str] = None

    @model_validator(mode="after")
    def black_box_contract(self) -> "EventCreate":
        """
        Black Box Contract enforcement.

        blind_payload guarantees privacy of content — but presence must be
        anchored. If blind_payload is set, both location and timestamp are
        mandatory and must be non-empty. This is not a policy; it is a
        structural condition for the event to exist.
        """
        if self.blind_payload is not None:
            if not self.location or not self.location.strip():
                raise ValueError(
                    "Black Box Contract violation: blind_payload requires a non-empty location. "
                    "Content may be hidden — presence may not."
                )
            if self.timestamp is None:
                raise ValueError(
                    "Black Box Contract violation: blind_payload requires an explicit timestamp. "
                    "Content may be hidden — the moment may not."
                )
        return self


class EventResponse(BaseModel):
    """Response model for event data."""
    id: str
    timestamp: float
    raw_data_anchor: List[str]
    location: str
    ttl: Optional[int] = None
    is_fused: bool = False
    fusion_count: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    encrypted_payload: Optional[str] = None
    blind_payload: Optional[str] = None


class BatchEventCreate(BaseModel):
    """Request model for batch event creation."""
    events: List[EventCreate]


class InterpretationResponse(BaseModel):
    """Model for interpretation results."""
    events: List[Dict[str, Any]]
    context_mood: str
    firewall_report: Optional[Dict[str, Any]] = None


class InterpretationRequest(BaseModel):
    """Request model for interpretation."""
    context: Dict[str, Any] = Field(default_factory=dict)
    temporal_query: Optional[str] = None
    limit: int = INTERPRET_LIMIT_DEFAULT
    firewall_mode: str = INTERPRET_FIREWALL_MODE_DEFAULT


class HealthStatus(BaseModel):
    """Health check response model."""
    project: Dict[str, str]
    status: str
    health_score: Optional[int] = None
    oom_prediction: Optional[Dict[str, Any]] = None
    database: Dict[str, Any]
    components: Dict[str, Any]
    system: Optional[Dict[str, Any]] = None
    endpoints: Dict[str, str]


class WebSocketSubscription(BaseModel):
    """WebSocket subscription configuration."""
    event_types: List[str] = Field(default_factory=lambda: ["all"])
    locations: List[str] = Field(default_factory=list)
    temporal_filter: Optional[str] = None
    min_relevance: float = 0.0


class WebhookRequest(BaseModel):
    """Webhook registration request."""
    url: str
