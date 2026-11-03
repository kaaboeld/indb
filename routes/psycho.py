"""
Psycho Routes (v2) — pathfinding under weight ablation.

    GET  /api/v2/psycho/profiles    the weight profiles and what each removes
    POST /api/v2/psycho/path        route between two anchors, with the comparison

Meaning stays with the observer here as everywhere else: the caller supplies the
valuation, and the profile only decides whether the route is allowed to feel it.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from auth.flexible_auth import optional_identity
from core.kernel import AuthContext
from core.routing import ContentNegotiationRoute
from core.psycho import (
    BASELINE_PROFILE_ID,
    DEFAULT_MAX_HOPS,
    DEFAULT_MAX_VISITED,
    PsychoEngine,
    get_profile,
    list_profiles,
)

router = APIRouter(
    prefix="/api/v2/psycho",
    tags=["Psycho (Pathfinding)"],
    route_class=ContentNegotiationRoute,
)


class PathRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source: str = Field(..., alias="from", description="Event id or free text for the start anchor")
    target: str = Field(..., alias="to", description="Event id or free text for the destination anchor")
    profile: str = Field("psychopath", description="Weight profile to probe with")
    compare_to: Optional[str] = Field(
        BASELINE_PROFILE_ID,
        description="Profile to measure against. Null skips the comparison.",
    )
    token_weights: Dict[str, float] = Field(
        default_factory=dict,
        description=(
            "The observer's valuation. Negative weights are what it costs them to "
            "route through a node carrying that token — the barrier a profile may ignore."
        ),
    )
    max_hops: int = Field(DEFAULT_MAX_HOPS, ge=1, le=12)
    max_visited: int = Field(DEFAULT_MAX_VISITED, ge=10, le=20000)


@router.get("/profiles")
async def psycho_profiles() -> Dict[str, Any]:
    """The available weight profiles and what each one removes."""
    return {
        "baseline": BASELINE_PROFILE_ID,
        "profiles": list_profiles(),
        "note": (
            "A path on its own is not the result. Compare a profile against the "
            "baseline: the divergence is what the removed weights were doing."
        ),
    }


@router.post("/path")
async def psycho_path(
    payload: PathRequest,
    request: Request,
    auth: AuthContext = Depends(optional_identity),
) -> Dict[str, Any]:
    """
    Route from one anchor to another, then measure the valuation by removing it.

    The cheapest path maximises the product of resonances along it, so it is the
    most plausible chain rather than merely the shortest.
    """
    indb = getattr(request.app.state, "indb", None)
    if not indb:
        raise HTTPException(status_code=503, detail="Psycho core not ready (INDB unavailable)")

    try:
        profile = get_profile(payload.profile)
        baseline = get_profile(payload.compare_to) if payload.compare_to else None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    engine = PsychoEngine(indb)

    source = engine.resolve_reference(payload.source)
    if source is None:
        raise HTTPException(status_code=404, detail=f"No event matches source anchor: {payload.source!r}")

    target = engine.resolve_reference(payload.target)
    if target is None:
        raise HTTPException(status_code=404, detail=f"No event matches target anchor: {payload.target!r}")

    search = {"max_hops": payload.max_hops, "max_visited": payload.max_visited}

    anchors = {
        "source": {"event_id": source.id, "location": str(source.location or ""), "tokens": list(source.raw_data_anchor or [])},
        "target": {"event_id": target.id, "location": str(target.location or ""), "tokens": list(target.raw_data_anchor or [])},
        "valuation": payload.token_weights,
    }

    if baseline is None:
        result = engine.find_path(source, target, profile, payload.token_weights, **search)
        return {"anchors": anchors, "result": result.to_dict(), "ablation": None}

    comparison = engine.compare(
        source, target, profile, baseline, payload.token_weights, **search
    )
    return {
        "anchors": anchors,
        "result": comparison["probe_path"],
        "ablation": comparison,
    }
