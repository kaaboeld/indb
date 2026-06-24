"""
Context Slice API — horizontal what-if in core (no LLM).

POST /api/v2/slice
Brick (seed) + abstract modifier → rescored edges + optional Prism overlay.
"""
from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from core.cognitive_pipeline import run_subwave_then_slice
from core.constants import WHAT_IF_SUBWAVE_DEFAULT
from core.models import StandardResponse
from core.observer_profiles import list_profile_ids, resolve_observer
from core.prism import ObserverContext
from core.context_slice import ContextSliceResult

router = APIRouter(prefix="/api/v2/slice", tags=["Slice (Horizontal Context)"])


class SliceRequest(BaseModel):
    seed_id: Optional[str] = None
    query: Optional[str] = None
    what_if: str = Field(..., min_length=1)
    radius: float = 0.3
    limit: int = 20
    observer_context: Optional[ObserverContext] = None
    observer_profile: Optional[str] = None
    use_subwave: bool = WHAT_IF_SUBWAVE_DEFAULT


class SlicePipelineResponse(ContextSliceResult):
    """Slice fields plus optional subwave lock frame (same top-level shape + subwave)."""
    subwave: Optional[Any] = None


@router.get("/causal/{seed_id}", response_model=StandardResponse[dict])
async def get_causal_links(
    seed_id: str,
    request: Request,
    direction: str = "both",
    limit: int = 20,
):
    """Temporal horizontal links (after / before / both)."""
    indb = getattr(request.app.state, "indb", None)
    if not indb:
        raise HTTPException(status_code=503, detail="INDB Core not ready")
    db = getattr(indb, "db", indb)
    causal = getattr(db, "causal_index", None)
    if causal is None:
        raise HTTPException(status_code=503, detail="Causal index not available")
    if direction not in ("after", "before", "both"):
        raise HTTPException(status_code=400, detail="direction must be after, before, or both")
    data = {
        "seed_id": seed_id,
        "direction": direction,
        "after": causal.links_after(seed_id, limit) if direction in ("after", "both") else [],
        "before": causal.links_before(seed_id, limit) if direction in ("before", "both") else [],
    }
    return StandardResponse(data=data, meta=causal.stats())


@router.get("/neighbors/{seed_id}", response_model=StandardResponse[dict])
async def get_persisted_neighbors(seed_id: str, request: Request, limit: int = 20):
    """Materialized horizontal edges for a seed (from resonance_edges.bin)."""
    indb = getattr(request.app.state, "indb", None)
    if not indb:
        raise HTTPException(status_code=503, detail="INDB Core not ready")
    db = getattr(indb, "db", indb)
    graph = getattr(db, "resonance_graph", None)
    if graph is None:
        raise HTTPException(status_code=503, detail="Resonance graph not available")
    edges = graph.get_edges(seed_id)[:limit]
    return StandardResponse(
        data={"seed_id": seed_id, "edges": edges},
        meta=graph.stats(),
    )


@router.get("/profiles", response_model=StandardResponse[List[str]])
async def list_observer_profiles():
    """Named observer presets (from OBSERVER_PROFILES_PATH JSON, if configured)."""
    return StandardResponse(data=list_profile_ids())


@router.post("", response_model=StandardResponse[SlicePipelineResponse])
async def context_slice(payload: SliceRequest, request: Request):
    """
    Horizontal slice from a seed (brick) and an abstract «what if» modifier.

    Default pipeline: Subwave broadcast (unified frequency) → Slice (shift + Prism).
    Set use_subwave=false for slice-only. No LLM.
    """
    if not payload.seed_id and not payload.query:
        raise HTTPException(status_code=400, detail="Provide seed_id or query.")

    indb = getattr(request.app.state, "indb", None)
    if not indb:
        raise HTTPException(status_code=503, detail="INDB Core not ready")

    try:
        observer = resolve_observer(payload.observer_profile, payload.observer_context)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        pipeline = await run_subwave_then_slice(
            indb,
            seed_id=payload.seed_id or "",
            query=payload.query,
            what_if=payload.what_if,
            observer=observer,
            radius=payload.radius,
            slice_limit=payload.limit,
            use_subwave=payload.use_subwave,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    data = SlicePipelineResponse(
        **pipeline.slice.model_dump(),
        subwave=pipeline.subwave.model_dump() if pipeline.subwave else None,
    )

    return StandardResponse(
        data=data,
        meta={
            "engine": "subwave+slice" if payload.use_subwave else "context_slice",
            "llm": False,
            "observer_profile": payload.observer_profile,
        },
    )
