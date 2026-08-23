"""
Deduction API — Sherlock Holmes Thinking

Given evidence (events), infers chains and conclusions.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List

from core.deduction import DeductionEngine, DeductionResult

from core.routing import ContentNegotiationRoute

router = APIRouter(
    prefix="/api/v2/deduction",
    tags=["Deduction (Inference)"],
    route_class=ContentNegotiationRoute,
)


class DeduceRequest(BaseModel):
    seed_event_ids: Optional[List[str]] = None
    """
    Direct event IDs to use as starting evidence.
    If provided, query is ignored.
    """
    query: Optional[str] = None
    """
    Text query to resolve to seed events (e.g. "birthday cheese", "beach 2024").
    Used when seed_event_ids is empty.
    """
    radius: float = 0.35
    """Echo resonance radius for expanding evidence cloud."""
    limit: int = 15
    """Max events to include in evidence chain."""


@router.post("/deduce", response_model=DeductionResult)
async def deduce(payload: DeduceRequest, request: Request):
    """
    Deduction — infer conclusions from evidence chains.

    Sherlock Holmes thinking: given facts (events), what can we infer?

    Pipeline:
    1. **Resolve seeds**: Use seed_event_ids or resolve query to closest events.
    2. **Expand**: Echo resonance from each seed → evidence cloud.
    3. **Chain**: Order by time, build inference steps (temporal, spatial, token).
    4. **Conclude**: Synthesize what the evidence suggests.

    Returns:
    - chain: Ordered inference steps with reasons
    - conclusion: Synthesized statement
    - confidence: 0.0–1.0
    - reasoning: Human-readable trace
    """
    indb = getattr(request.app.state, "indb", None)
    if not indb:
        raise HTTPException(status_code=503, detail="INDB Core not ready")

    if not payload.seed_event_ids and not payload.query:
        raise HTTPException(
            status_code=400,
            detail="Provide either seed_event_ids or query.",
        )

    engine = DeductionEngine(indb)
    return await engine.deduce(
        seed_event_ids=payload.seed_event_ids,
        query=payload.query,
        radius=payload.radius,
        limit=payload.limit,
    )
