"""
Grain API — verification across the noise-tolerance spectrum.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from core.grain import GrainConfig, GrainEngine, GrainResult, TIER_CATALOG
from core.grain.models import GrainTierInput
from core.models import StandardResponse

router = APIRouter(prefix="/api/v2/grain", tags=["Grain (Identity Tolerance)"])


class GrainVerifyRequest(BaseModel):
    """Verify candidate identity against reference event(s)."""

    candidate: Dict[str, Any] = Field(
        description="Event dict or partial event (raw_data_anchor, optional signature).",
    )
    reference_event_id: Optional[str] = Field(
        default=None,
        description="Primary seed event for resonant / statistical tiers.",
    )
    reference_event_ids: Optional[List[str]] = Field(
        default=None,
        description="Event cluster for redundant tier (N-of-M signatures).",
    )
    expected_key_id: Optional[str] = Field(
        default=None,
        description="Ed25519 public identity hash for exact / redundant tiers.",
    )
    tier: GrainTierInput = "auto"
    tolerance: float = Field(default=0.5, ge=0.0, le=1.0)
    min_tokens: int = Field(default=20, ge=1)
    min_events: int = Field(default=3, ge=1)
    damage_ratio: float = Field(default=0.30, ge=0.0, le=1.0)


class GrainVerifyResponse(BaseModel):
    result: GrainResult


@router.get("/tiers", response_model=StandardResponse[List[Any]])
async def list_tiers():
    """
    Return the noise-tolerance spectrum: exact → redundant → resonant → statistical.

    Analogies: barcode → QR → handwritten signature → SynthID.
    """
    return StandardResponse(data=[t.model_dump() for t in TIER_CATALOG])


@router.post("/verify", response_model=StandardResponse[GrainResult])
async def verify_identity(payload: GrainVerifyRequest, request: Request):
    """
    Verify whether a candidate event shares origin with reference(s).

    **Tiers:**
    - `exact` — Ed25519 signature (~0% noise)
    - `redundant` — N-of-M signed cluster (~30% damage)
    - `resonant` — Echo × reputation (~30–50%, FAR/FRR via tolerance)
    - `statistical` — n-gram distribution p-value (SynthID-like)
    - `auto` — engine selects tier from available evidence

    **Tolerance knob** (0.0–1.0): strict → permissive. Controls false accept vs false reject.
    """
    indb = getattr(request.app.state, "indb", None)
    if not indb:
        raise HTTPException(status_code=503, detail="INDB Core not ready")

    config = GrainConfig(
        tier=payload.tier,
        tolerance=payload.tolerance,
        min_tokens=payload.min_tokens,
        min_events=payload.min_events,
        damage_ratio=payload.damage_ratio,
    )

    engine = GrainEngine(indb)
    result = engine.verify(
        candidate=payload.candidate,
        reference_event_id=payload.reference_event_id,
        reference_event_ids=payload.reference_event_ids,
        expected_key_id=payload.expected_key_id,
        config=config,
    )

    return StandardResponse(data=result)
