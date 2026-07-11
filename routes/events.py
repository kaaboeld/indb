"""
Event Ingestion Routes (v2)

Handles event creation, batch operations, and webhooks.
"""
import time
import json
import httpx
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Request, HTTPException

from core.kernel import AuthContext
from core.deps import IndbDep
from core.rate_limit import limiter, RateLimits
from core.models import (
    StandardResponse,
    EventCreate,
    EventResponse,
    BatchEventCreate,
    WebhookRequest
)

router = APIRouter(prefix="/api/v2", tags=["events"])


@router.post("/events", response_model=StandardResponse[EventResponse])
@limiter.limit(RateLimits.INGEST)
async def create_event(request: Request, event: EventCreate, db: IndbDep):
    """Create a new event (v2)."""
    try:
        # ── Black Box Contract ─────────────────────────────────────────────────
        # If blind_payload is present:
        #   1. location is REQUIRED — the fact of presence must be anchored.
        #   2. timestamp must be within ±5 minutes — prevents replay attacks.
        # "You may hide what is inside. You may not hide that you were here."
        if event.blind_payload:
            if not event.location:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "blind_payload requires location",
                        "reason": "Black box events must be spatially anchored. "
                                  "You may hide the contents — not the presence."
                    }
                )
            event_ts = event.timestamp if hasattr(event, 'timestamp') and event.timestamp else time.time()
            if abs(time.time() - event_ts) > 300:  # 5 minute window
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "blind_payload timestamp out of window",
                        "reason": "Timestamp must be within ±5 minutes of server time. "
                                  "Possible replay attack detected."
                    }
                )
        # ──────────────────────────────────────────────────────────────────────

        # Use Kernel Wrapper to trigger Webhooks
        auth = AuthContext(user_id="api_writer", auth_method="api_key")

        event_data = {
            "raw_data_anchor": event.raw_data_anchor,
            "location": event.location,
            "id": event.id,
            "timestamp": event.timestamp,
            "ttl": event.ttl,
            "blind_payload": event.blind_payload,
            "signature": event.signature,
        }

        try:
            new_event_dict = await db.create_event(event_data, auth)
        except ValueError as exc:
            if "signature" in str(exc).lower():
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            raise

        response_data = EventResponse(
            id=new_event_dict["id"],
            timestamp=new_event_dict["timestamp"],
            raw_data_anchor=new_event_dict["raw_data_anchor"],
            location=new_event_dict["location"],
            ttl=new_event_dict.get("ttl"),
            blind_payload=new_event_dict.get("blind_payload"),
            signature=new_event_dict.get("signature"),
            is_fused="fusion_count" in new_event_dict,
            fusion_count=new_event_dict.get("fusion_count"),
        )

        meta = {}
        if "fusion_count" in new_event_dict:
            meta["fusion"] = {
                "strategy": new_event_dict.get("fusion_strategy", "unknown"),
                "pattern": new_event_dict.get("pattern", "unknown"),
            }

        # Note: WebSocket broadcast will be handled via event bus in future refactoring
        # For now keeping dependency on main.py manager

        return StandardResponse(data=response_data, meta=meta)

    except Exception as e:
        if "RedirectToLeader" in str(e):
            leader_id = str(e).split(":")[1]
            print(f"🔄 Proxying request to Leader: {leader_id}")
            
            try:
                # Proxy to Leader directly via internal docker network
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(
                        f"http://{leader_id}:8000/api/v2/events", 
                        json=event.model_dump()
                    )
                    # Return the raw JSON response from the leader
                    return resp.json()
            except Exception as proxy_err:
                print(f"Proxy Error: {proxy_err}")
                raise HTTPException(status_code=503, detail=f"Leader {leader_id} unavailable")
        
        # Re-raise other errors
        raise e


@router.post("/events/batch", response_model=StandardResponse[Dict[str, Any]])
async def create_events_batch(batch: BatchEventCreate, db: IndbDep):
    """
    Create multiple events in a single request (v2).
    
    Supports bulk insertion with automatic fusion and rollback on critical errors.
    If this node is a Raft follower, the entire batch is proxied to the leader.
    """
    start_time = time.time()
    
    if not batch.events:
        raise HTTPException(status_code=400, detail="No events provided")
    
    if len(batch.events) > 1000:
        raise HTTPException(status_code=400, detail="Batch size exceeds maximum of 1000 events")
    
    created_events = []
    fused_count = 0
    errors = []
    leader_id = None
    
    # Process each event — detect redirect on first failure
    for idx, event_data in enumerate(batch.events):
        try:
            new_event = await db.db.ingest(
                raw_data_anchor=event_data.raw_data_anchor,
                location=event_data.location,
                ttl=event_data.ttl
            )
            
            created_events.append({
                "id": new_event.id,
                "timestamp": new_event.timestamp,
                "is_fused": hasattr(new_event, "fusion_count"),
            })
            
            if hasattr(new_event, "fusion_count"):
                fused_count += 1
                
        except Exception as e:
            err_str = str(e)
            if "RedirectToLeader" in err_str and leader_id is None:
                leader_id = err_str.split(":")[1].strip()
                break  # proxy the whole batch to leader instead
            errors.append({
                "index": idx,
                "error": err_str,
                "event": event_data.model_dump()
            })
    
    # If follower redirect detected — proxy entire batch to leader
    if leader_id:
        print(f"🔄 Proxying batch to Leader: {leader_id}")
        try:
            async with httpx.AsyncClient(timeout=120.0) as proxy_client:
                resp = await proxy_client.post(
                    f"http://{leader_id}:8000/api/v2/events/batch",
                    json=batch.model_dump()
                )
                return resp.json()
        except Exception as proxy_err:
            print(f"Proxy Error: {proxy_err}")
            raise HTTPException(status_code=503, detail=f"Leader {leader_id} unavailable: {proxy_err}")
    
    processing_time = time.time() - start_time
    
    data = {
        "total_submitted": len(batch.events),
        "total_created": len(created_events),
        "total_fused": fused_count,
        "total_errors": len(errors),
        "created_events": created_events[:10],  # Return first 10 for preview
        "errors": errors[:5],  # Return first 5 errors
    }
    
    return StandardResponse(
        data=data,
        meta={
            "performance": {
                "processing_time_ms": round(processing_time * 1000, 2),
                "events_per_second": round(len(created_events) / processing_time if processing_time > 0 else 0, 2),
            },
            "truncated": {
                "events": len(created_events) > 10,
                "errors": len(errors) > 5,
            }
        },
        status="success" if len(errors) == 0 else "partial_success"
    )

# Webhook Management endpoints use WebhookRequest from core.models

@router.post("/webhooks", response_model=StandardResponse[Dict[str, str]])
async def register_webhook(webhook: WebhookRequest, db: IndbDep):
    """Register a new webhook URL."""
    db.webhooks.register(webhook.url)
    return StandardResponse(data={"status": "registered", "url": webhook.url})


@router.delete("/webhooks", response_model=StandardResponse[Dict[str, str]])
async def unregister_webhook(webhook: WebhookRequest, db: IndbDep):
    """Unregister a webhook URL."""
    db.webhooks.unregister(webhook.url)
    return StandardResponse(data={"status": "unregistered", "url": webhook.url})
