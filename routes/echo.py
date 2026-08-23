from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import List, Optional
from core.echo import ResonanceEngine, ResonanceResult

from core.routing import ContentNegotiationRoute

router = APIRouter(
    prefix="/api/v2/echo",
    tags=["Echo (Resonance)"],
    route_class=ContentNegotiationRoute,
)

class ResonateRequest(BaseModel):
    seed_id: str
    radius: float = 0.3
    limit: int = 20

class EchoResponse(BaseModel):
    center: str
    ripples: List[ResonanceResult]

@router.post("/resonate", response_model=EchoResponse)
async def trigger_resonance(payload: ResonateRequest, request: Request):
    """
    Trigger a Resonance Wave from a seed event.
    Returns a cloud of related events based on harmonic proximity.
    """
    # Access INDB instance from app state (populated in main.py/app_factory)
    indb = getattr(request.app.state, "indb", None)
    
    if not indb:
        raise HTTPException(status_code=503, detail="Resonance Core not ready (INDB unavailable)")

    engine = ResonanceEngine(indb)
    
    # Calculate resonance
    ripples = await engine.resonate(
        seed_event_id=payload.seed_id,
        radius=payload.radius,
        limit=payload.limit
    )
    
    return EchoResponse(
        center=payload.seed_id,
        ripples=ripples
    )
