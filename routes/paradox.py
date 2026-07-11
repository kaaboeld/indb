"""
Paradox API — pre-observation superposition (separate from Event).

POST /api/v2/paradox — create superposed paradox (context only)
GET  /api/v2/paradox/{id}?collapse=true — observe / collapse
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from core.deps import IndbDep
from core.models import StandardResponse
from core.paradox import ParadoxEngine

router = APIRouter(prefix="/api/v2/paradox", tags=["Paradox (Pre-Observation Type)"])


class ParadoxCreate(BaseModel):
    location: str = Field(description="Spatial anchor — where superposition lives")
    paradox_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="themes, token_pool, etc.",
    )
    paradox_generation: Optional[Dict[str, Any]] = Field(
        default=None,
        description='{"mode": "resonance_weighted|pool|fusion", "collapse": "sample_once|sample_on_read"}',
    )


@router.post("", response_model=StandardResponse[Dict[str, Any]])
async def create_paradox(payload: ParadoxCreate, db: IndbDep):
    """
    Create a Paradox — not an Event.

    `raw_data_anchor` stays empty until observation.
    Private keys are irrelevant here; paradox holds context, not writer identity.
    """
    engine = ParadoxEngine(db)
    try:
        paradox = engine.create(
            location=payload.location,
            paradox_context=payload.paradox_context,
            paradox_generation=payload.paradox_generation,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return StandardResponse(
        data=paradox.to_dict(),
        meta={"entity": "paradox", "state": paradox.state},
    )


@router.get("/{paradox_id}", response_model=StandardResponse[Dict[str, Any]])
async def get_paradox(
    paradox_id: str,
    db: IndbDep,
    collapse: bool = Query(
        default=False,
        description="If true, collapse superposition and sample anchor",
    ),
):
    """
    Read paradox. Pass `collapse=true` to observe.

    - `sample_once`: first collapse fixes anchor and may create Event (`event_id`)
    - `sample_on_read`: each collapse returns new anchor; stays superposed
    """
    if collapse:
        engine = ParadoxEngine(db)
        try:
            paradox = await engine.collapse(paradox_id)
        except ValueError as exc:
            msg = str(exc)
            if "not found" in msg.lower():
                raise HTTPException(status_code=404, detail=msg) from exc
            raise HTTPException(status_code=422, detail=msg) from exc
        return StandardResponse(
            data=paradox.to_dict(),
            meta={"collapsed": True, "collapse_mode": paradox.paradox_generation.collapse},
        )

    paradox = db.get_paradox(paradox_id)
    if not paradox:
        raise HTTPException(status_code=404, detail="Paradox not found")

    return StandardResponse(data=paradox.to_dict(), meta={"collapsed": False})
