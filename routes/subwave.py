"""
Subwave API — unified resonance broadcast from an anchor.

POST /api/v2/subwave/broadcast
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from core.models import StandardResponse
from core.observer_profiles import resolve_observer
from core.prism import ObserverContext
from core.subwave import SubwaveEngine, SubwaveResult

router = APIRouter(prefix="/api/v2/subwave", tags=["Subwave (Unified Resonance)"])


class SubwaveBroadcastRequest(BaseModel):
    seed_id: Optional[str] = None
    query: Optional[str] = None
    modifier: Optional[str] = Field(
        None,
        description="Optional what-if phrase — tunes the broadcast frequency",
    )
    radius: float = 0.3
    limit: int = 50
    lock_threshold: float = 0.35
    observer_context: Optional[ObserverContext] = None
    observer_profile: Optional[str] = None


@router.post("/broadcast", response_model=StandardResponse[SubwaveResult])
async def subwave_broadcast(payload: SubwaveBroadcastRequest, request: Request):
    """
    Subwave broadcast: anchor (seed) emits one frequency; nodes lock in horizontally.

    Uses graph + causal + index + semantic pool, then scores all candidates against
    a unified signature (anchor tokens + optional modifier). No LLM.
    """
    if not payload.seed_id and not payload.query:
        raise HTTPException(status_code=400, detail="Provide seed_id or query.")

    indb = getattr(request.app.state, "indb", None)
    if not indb:
        raise HTTPException(status_code=503, detail="INDB Core not ready")

    try:
        resolve_observer(payload.observer_profile, payload.observer_context)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    engine = SubwaveEngine(indb)
    try:
        result = await engine.broadcast(
            seed_id=payload.seed_id or "",
            query=payload.query,
            modifier=payload.modifier,
            radius=payload.radius,
            limit=payload.limit,
            lock_threshold=payload.lock_threshold,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return StandardResponse(
        data=result,
        meta={"engine": "subwave", "llm": False},
    )
