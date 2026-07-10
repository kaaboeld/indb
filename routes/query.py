"""
Query & Interpretation Routes (v2)

Handles data retrieval, search, and semantic interpretation.
"""
import json
import csv
import io
import time
from typing import List, Dict, Any, Optional, Tuple, Type
from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import StreamingResponse

from core.kernel import AuthContext, QueryRequest
from core.deps import IndbDep
from core.constants import INTERPRET_MOOD_DEFAULT, EVENT_RESPONSE_MISSING_ID, EVENT_RESPONSE_MISSING_LOCATION
from core.rate_limit import limiter, RateLimits
from core.models import (
    StandardResponse,
    EventResponse,
    InterpretationRequest,
    InterpretationResponse
)
from services.interpretation.emotional_firewall import EmotionalFirewall, FirewallMode
from services.ml.emotion_classifier import EmotionClassifier
from services.query.advanced_filter import AdvancedFilter, FilterCriteria
from services import ML_AVAILABLE

router = APIRouter(prefix="/api/v2", tags=["query"])


@router.get("/events", response_model=StandardResponse[List[EventResponse]])
async def list_events(
    db: IndbDep,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    filter_key: Optional[str] = None,
    filter_value: Optional[str] = None,
    context_mood: Optional[str] = None,
):
    """List all events with pagination and filtering (v2)."""
    mood = context_mood or INTERPRET_MOOD_DEFAULT

    query = QueryRequest(
        limit=limit,
        offset=offset,
        filter_key=filter_key,
        filter_value=filter_value,
        context_mood=mood,
    )
    
    try:
        events = db.query(query, AuthContext(user_id="api_reader"))
    except Exception:
        events = []

    # Map back to response model
    data = []
    for e_dict in events:
        # Check if e_dict is already a dict or object
        if hasattr(e_dict, "id"):
             e_dict = e_dict.to_dict()
             
        data.append(EventResponse(
            id=str(e_dict.get("id", EVENT_RESPONSE_MISSING_ID) or EVENT_RESPONSE_MISSING_ID),
            timestamp=float(e_dict.get("timestamp", 0.0)),
            raw_data_anchor=e_dict.get("raw_data_anchor", []),
            location=str(e_dict.get("location", EVENT_RESPONSE_MISSING_LOCATION) or EVENT_RESPONSE_MISSING_LOCATION),
            ttl=e_dict.get("ttl"),
            metadata=e_dict.get("metadata", {}),
            encrypted_payload=e_dict.get("encrypted_payload"),
            blind_payload=e_dict.get("blind_payload"),
            is_fused=e_dict.get("is_fused", False),
            fusion_count=e_dict.get("fusion_count"),
        ))

    return StandardResponse(
        data=data,
        meta={
            "pagination": {
                "total": db.get_event_count(),
                "limit": limit,
                "offset": offset
            },
            "filters": {
                "key": filter_key,
                "value": filter_value,
                "mood": mood
            }
        }
    )


def _calculate_relevance(event, query_tokens: set, query_lower: str, fuzzy: bool) -> Tuple[float, List[str]]:
    """Helper to calculate relevance score for search."""
    # Base Score (Match Counter)
    score = 0.0
    matches = []
    event_tokens = [t.lower() for t in event.raw_data_anchor]
    
    # 1. Base Token Matching
    for token in event_tokens:
        # Handle key:value tokens
        token_parts = token.split(":", 1)
        token_val = token_parts[1] if len(token_parts) > 1 else token
        
        if fuzzy:
            for q_token in query_tokens:
                if q_token in token or token in q_token:
                    score += 2.0
                    matches.append(token)
        else:
            # Exact matching (relaxed to value matching)
            # If query token matches the VALUE part of a key:value token
            for q_token in query_tokens:
                if q_token == token or q_token == token_val:
                    score += 2.0
                    matches.append(token)
                
    # 2. Location Matching
    # Check if any query token is in location
    if any(qt in event.location.lower() for qt in query_tokens):
            score += 1.0
            matches.append(f"location:{event.location}")

    if score == 0:
        return 0.0, []

    # === PENALTY LAYERS (Critical Thinking) ===
    
    # Layer 1: Era Mismatch Penalty
    if any("era:ancient" in t for t in event_tokens) and "ancient" not in query_lower:
        score *= 0.7  # -30% confidence for unrequested ancient events

    # Layer 2: Location Consistency Penalty
    osm_locs = set(t for t in event_tokens if t.startswith("osm:"))
    if len(osm_locs) > 1:
        penalty = (len(osm_locs) - 1) * 3.0
        score -= penalty

    # Layer 3: Temporal Outlier Penalty (Seasonality Check)
    query_months = [m for m in ["-01-", "-02-", "-03-", "-04-", "-05-", "-06-", "-07-", "-08-", "-09-", "-10-", "-11-", "-12-"] if m in query_lower]
    if query_months:
        timestamps = [t for t in event_tokens if t.startswith("timestamp:")]
        outliers = 0
        for ts in timestamps:
            if not any(qm in ts for qm in query_months):
                outliers += 1
        
        if outliers > 0:
            score -= (outliers * 2.0)

    return max(0.0, score), matches


@router.get("/search", response_model=StandardResponse[List[Dict[str, Any]]])
async def search_events(
    db: IndbDep,
    q: str = Query(..., description="Search query"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    fuzzy: bool = Query(False, description="Enable fuzzy matching"),
):
    """
    Full-text search across events (v2).
    
    Searches through raw_data_anchor tokens and location fields.
    Returns results sorted by relevance score.
    """
    query_lower = q.lower()
    query_tokens = set(query_lower.split())
    
    results = []
    
    for event in db.iter_events():
        score, matches = _calculate_relevance(event, query_tokens, query_lower, fuzzy)
        
        if score > 0:
            results.append({
                "event": EventResponse(
                    id=event.id,
                    timestamp=event.timestamp,
                    raw_data_anchor=event.raw_data_anchor,
                    location=event.location,
                    ttl=event.ttl,
                    is_fused=hasattr(event, "fusion_count"),
                    fusion_count=getattr(event, "fusion_count", 0) if hasattr(event, "fusion_count") else None,
                ),
                "relevance_score": round(score, 2),
                "matches": list(set(matches))[:5],  # Unique matches, limit to 5
            })
    
    # Sort by relevance score (descending)
    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    
    # Pagination
    total_count = len(results)
    paginated_results = results[offset : offset + limit]
    
    # Extract just the event data for response
    data = [
        {
            "id": r["event"].id,
            "timestamp": r["event"].timestamp,
            "raw_data_anchor": r["event"].raw_data_anchor,
            "location": r["event"].location,
            "relevance_score": r["relevance_score"],
            "matches": r["matches"],
            "is_fused": r["event"].is_fused,
        }
        for r in paginated_results
    ]
    
    return StandardResponse(
        data=data,
        meta={
            "query": q,
            "fuzzy": fuzzy,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "count": len(data),
            },
        },
    )


@router.post("/interpret", response_model=StandardResponse[InterpretationResponse])
@limiter.limit(RateLimits.BURST)
async def interpret_events(request: Request, payload: InterpretationRequest, db: IndbDep):
    """
    Interpret events based on context (v2).
    """
    context = payload.context
    temporal_query = payload.temporal_query
    # limit = payload.limit # Unused directly in logic below?
    firewall_mode = payload.firewall_mode

    # Get context mood (input from request)
    mood = context.get("mood", INTERPRET_MOOD_DEFAULT)

    # Get raw events first
    raw_events = list(db.iter_events())

    # Apply temporal filter BEFORE interpretation
    if temporal_query:
        raw_events = db.db.filter_by_temporal_query(raw_events, temporal_query)

    # Now scan/interpret the filtered events
    try:
        events = db.db.scan("", "", context_mood=mood, events_to_scan=raw_events)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Interpretation failed: {str(e)}")

    # Apply emotional firewall if not in therapy mode
    firewall_report = None
    if firewall_mode != "therapy":
        mode_map = {
            "block": FirewallMode.BLOCK,
            "redact": FirewallMode.REDACT,
            "warning": FirewallMode.WARNING,
            "therapy": FirewallMode.THERAPY,
        }
        firewall = EmotionalFirewall(mode=mode_map.get(firewall_mode, FirewallMode.BLOCK))

        # Initialize classifier
        classifier = EmotionClassifier()
        
        # Convert events to dict format for firewall
        events_for_fw = []
        for e in events:
            # Handle both dict and object
            anchor = e.get("raw_data_anchor", []) if isinstance(e, dict) else e.raw_data_anchor
            # Basic conversion for firewall check
            events_for_fw.append({
                "id": e.get("id") if isinstance(e, dict) else e.id,
                "raw_data_anchor": anchor,
                "derived_emotion": INTERPRET_MOOD_DEFAULT  # Placeholder, updated by classifier
            })

        # Process through firewall
        # Note: EmotionalFirewall.process expects a list of event dicts
        # We need to recreate the logic from main.py where it iterates and classifies
        
        filtered_events = []
        blocked_count = 0
        redacted_count = 0
        warnings = []

        for evt in events:
            evt_dict = evt if isinstance(evt, dict) else evt.to_dict()
            
            # Classify emotion
            tokens = evt_dict.get("raw_data_anchor", [])
            emotion = classifier.classify(tokens)
            evt_dict["derived_emotion"] = emotion.value

            # Check firewall
            allowed, action, reason = firewall.check(evt_dict)

            if not allowed:
                blocked_count += 1
                continue # Skip event
            
            if action == "redact":
                # Redact logic
                evt_dict["raw_data_anchor"] = ["REDACTED"]
                evt_dict["blind_payload"] = None
                redacted_count += 1
            
            if action == "warn":
                warnings.append(f"Event {evt_dict.get('id')} triggered warning: {reason}")
                evt_dict["firewall_warning"] = reason

            filtered_events.append(evt_dict)
            
        events = filtered_events # Replace result with filtered list
        
        firewall_report = {
            "mode": firewall_mode,
            "blocked": blocked_count,
            "redacted": redacted_count,
            "warnings": warnings
        }

    return StandardResponse(
        data=InterpretationResponse(
            events=[e if isinstance(e, dict) else e.to_dict() for e in events],
            context_mood=mood,
            firewall_report=firewall_report
        )
    )


def _event_to_response(e) -> EventResponse:
    """Convert Event or FusedEvent to EventResponse (input → output, no hardcoding)."""
    return EventResponse(
        id=getattr(e, "id", None) or EVENT_RESPONSE_MISSING_ID,
        timestamp=float(getattr(e, "timestamp", 0.0)),
        raw_data_anchor=getattr(e, "raw_data_anchor", []) or [],
        location=str(getattr(e, "location", None) or EVENT_RESPONSE_MISSING_LOCATION),
        ttl=getattr(e, "ttl", None),
        is_fused=bool(getattr(e, "fusion_count", 0) > 1 or getattr(e, "is_fused", False)),
        fusion_count=getattr(e, "fusion_count", 0) or None,
    )


@router.post("/events/query", response_model=StandardResponse[List[EventResponse]])
async def query_events_advanced(criteria: FilterCriteria, db: IndbDep):
    """
    Advanced event filtering (v2).
    
    Supports:
    - Recursive criteria (AND/OR)
    - Field comparisons (eq, contains, gt, lt, in)
    """
    start_time = time.time()
    
    try:
        events = list(db.iter_events())
        filtered_events = AdvancedFilter.filter_stream(events, criteria)
        data = [_event_to_response(e) for e in filtered_events]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Advanced filter failed: {str(e)}")
    
    processing_time = time.time() - start_time
    
    return StandardResponse(
        data=data,
        meta={
            "performance": {
                "processing_time_ms": round(processing_time * 1000, 2),
                "total_events": len(events),
                "filtered_count": len(data)
            },
            "criteria": criteria.model_dump()
        }
    )


@router.get("/export/json")
async def export_json(db: IndbDep, filters: Optional[str] = Query(None, description="URL-encoded JSON FilterCriteria")):
    """
    Export events to JSON with optional filtering.
    """
    events = list(db.iter_events())
    
    # Apply filters if provided
    if filters:
        try:
            criteria_dict = json.loads(filters)
            criteria = FilterCriteria(**criteria_dict)
            events = AdvancedFilter.filter_stream(events, criteria)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid filters: {str(e)}")
            
    # Generator for streaming response
    def iter_json():
        yield "["
        for i, event in enumerate(events):
            if i > 0:
                yield ","
            # Use event.to_dict() if available, else manual dict creation
            if hasattr(event, "to_dict"):
                data = event.to_dict()
            else:
                data = {
                    "id": event.id,
                    "timestamp": event.timestamp,
                    "location": event.location,
                    "raw_data_anchor": event.raw_data_anchor,
                    "ttl": event.ttl
                }
            yield json.dumps(data)
        yield "]"
        
    return StreamingResponse(
        iter_json(),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=indb_export_{int(time.time())}.json"}
    )


@router.get("/export/csv")
async def export_csv(db: IndbDep, filters: Optional[str] = Query(None, description="URL-encoded JSON FilterCriteria")):
    """
    Export events to CSV with optional filtering.
    """
    events = list(db.iter_events())
    
    # Apply filters if provided
    if filters:
        try:
            criteria_dict = json.loads(filters)
            criteria = FilterCriteria(**criteria_dict)
            events = AdvancedFilter.filter_stream(events, criteria)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid filters: {str(e)}")
            
    # Generator for streaming response
    def iter_csv():
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(["id", "timestamp", "location", "tokens", "is_fused", "fusion_count"])
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)
        
        for event in events:
            tokens = "|" .join(event.raw_data_anchor)
            is_fused = hasattr(event, "fusion_count")
            fusion_count = getattr(event, "fusion_count", 0) if is_fused else 0
            
            writer.writerow([
                event.id,
                event.timestamp,
                event.location,
                tokens,
                is_fused,
                fusion_count
            ])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)
            
    return StreamingResponse(
        iter_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=indb_export_{int(time.time())}.csv"}
    )


def _find_similar_by_tokens(source_event, all_events, exclude_id, threshold, limit):
    """Fallback similarity using token overlap."""
    source_tokens = set(source_event.raw_data_anchor)
    similar = []

    for e in all_events:
        if e.id != exclude_id:
            event_tokens = set(e.raw_data_anchor)
            overlap = len(source_tokens & event_tokens)
            total = len(source_tokens | event_tokens)
            similarity = overlap / total if total > 0 else 0.0

            if similarity >= threshold:
                similar.append(
                    {
                        "id": e.id,
                        "location": e.location,
                        "tokens": e.raw_data_anchor[:5],
                        "timestamp": e.timestamp,
                        "similarity": round(similarity, 3),
                        "shared_tokens": list(source_tokens & event_tokens)[:5],
                        "is_fused": hasattr(e, "fusion_count"),
                    }
                )

    similar.sort(key=lambda x: x["similarity"], reverse=True)
    return similar[:limit]


@router.get("/events/{event_id}/associations", response_model=StandardResponse[Dict[str, Any]])
async def get_event_associations(event_id: str, db: IndbDep, limit: int = 10, threshold: float = 0.3):
    """
    Get semantically similar events using ML embeddings (v2).
    """
    # Find source event
    source_event = None
    for e in db.iter_events():
        if e.id == event_id:
            source_event = e
            break

    if not source_event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Use ML semantic embeddings if available
    method_used = "token_overlap"

    if ML_AVAILABLE:
        try:
            from services.ml.embeddings import SemanticEmbeddings

            embeddings = SemanticEmbeddings()

            source_tokens = source_event.raw_data_anchor
            similar_events = []

            for e in db.iter_events():
                if e.id != event_id:
                    similarity = embeddings.calculate_similarity(source_tokens, e.raw_data_anchor)
                    if similarity >= threshold:
                        similar_events.append(
                            {
                                "id": e.id,
                                "location": e.location,
                                "tokens": e.raw_data_anchor[:5],
                                "timestamp": e.timestamp,
                                "similarity": round(similarity, 3),
                                "is_fused": hasattr(e, "fusion_count"),
                            }
                        )

            similar_events.sort(key=lambda x: x["similarity"], reverse=True)
            similar_events = similar_events[:limit]
            method_used = "ml_embeddings"

        except ImportError:
            # Fallback
            similar_events = _find_similar_by_tokens(
                source_event, list(db.iter_events()), event_id, threshold, limit
            )
    else:
        # Fallback
        similar_events = _find_similar_by_tokens(
            source_event, list(db.iter_events()), event_id, threshold, limit
        )

    data = {
        "source_event": {
            "id": event_id,
            "location": source_event.location,
            "tokens": source_event.raw_data_anchor[:5],
        },
        "similar_events": similar_events,
        "count": len(similar_events),
    }

    return StandardResponse(
        data=data,
        meta={"threshold": threshold, "method": method_used, "ml_available": ML_AVAILABLE},
    )
