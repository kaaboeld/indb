from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
from core.prism import PrismEngine, PrismResult
from core.echo import ResonanceEngine
from core.instinct import (
    apply_adrenaline,
    detect_reflex_triggers,
    calculate_instinct_resonance,
    InstinctResult
)

router = APIRouter(prefix="/api/v2/prism", tags=["Prism (Instinct)"])

class InstinctRequest(BaseModel):
    query: str
    identity_key: Optional[str] = None
    adrenaline: float = 0.5  # 0.0 = analytical, 1.0 = pure instinct
    radius: float = 0.2
    limit: int = 20

class InstinctResponse(BaseModel):
    event: dict
    meaning: dict
    instinct: dict
    signature: dict

@router.post("/instinct", response_model=InstinctResponse)
async def instinct_synthesis(payload: InstinctRequest, request: Request):
    """
    Instinctive Cognitive Synthesis with Adrenaline.
    
    Shifts from analytical observation to instinctive reaction:
    - Low adrenaline (0.0-0.3): Analytical mode (balanced weights)
    - Medium adrenaline (0.3-0.7): Alert mode (moderate bias)
    - High adrenaline (0.7-1.0): Instinctive mode (reflex-driven)
    
    Reflex Triggers:
    - Owner signature match: +0.8 bonus
    - Location match: +0.7 bonus
    - Critical tokens: +0.5 bonus
    
    Returns:
    - Standard Prism result
    - Reflex arc trace
    - Instinct confidence score
    """
    indb = getattr(request.app.state, "indb", None)
    if not indb:
        raise HTTPException(status_code=503, detail="INDB Core not ready")
    
    # Validate adrenaline
    if not 0.0 <= payload.adrenaline <= 1.0:
        raise HTTPException(
            status_code=400, 
            detail="Adrenaline must be between 0.0 and 1.0"
        )
    
    echo_engine = ResonanceEngine(indb)
    prism_engine = PrismEngine(indb)
    
    # Apply adrenaline to Echo weights
    if payload.adrenaline > 0:
        adjusted_weights = apply_adrenaline(echo_engine.weights, payload.adrenaline)
        echo_engine.set_weights(adjusted_weights)
    
    # Get resonance cloud (Echo will use adjusted weights)
    cloud = await echo_engine.resonate(
        seed_event_id=payload.query,
        radius=payload.radius,
        limit=payload.limit
    )
    
    if not cloud:
        raise HTTPException(
            status_code=404, 
            detail="No resonance found (Silence)."
        )
    
    # Get seed event for instinct calculation
    seed = indb.get_event(payload.query)
    if not seed:
        raise HTTPException(status_code=404, detail="Seed event not found")
    
    # Enhance resonance results with instinct data
    instinct_results = []
    for res in cloud:
        target = indb.get_event(res.event_id)
        if target:
            instinct = calculate_instinct_resonance(
                seed=seed,
                target=target,
                base_resonance_score=res.score,
                adrenaline=payload.adrenaline
            )
            instinct_results.append(instinct)
    
    # Sort by instinct confidence if in instinctive mode
    if payload.adrenaline > 0.5:
        instinct_results.sort(key=lambda x: x.instinct_confidence, reverse=True)
    else:
        instinct_results.sort(key=lambda x: x.resonance_score, reverse=True)
    
    if not instinct_results:
        raise HTTPException(
            status_code=404,
            detail="Prism could not crystallize a result."
        )
    
    # Get top result
    top_instinct = instinct_results[0]
    top_event = indb.get_event(top_instinct.event_id)
    
    if not top_event:
        raise HTTPException(status_code=404, detail="Top event not found")
    
    # Synthesize with Prism (using original cloud for now)
    prism_result = prism_engine.synthesize(
        query=payload.query,
        identity_key=payload.identity_key,
        resonance_cloud=cloud
    )
    
    # Build response
    import time
    
    # Create simple signature dict (no crypto module needed)
    sig = {
        "algorithm": "Ed25519",
        "public_key": "instinct_module",
        "signature": f"instinct_{top_event.id}_{payload.adrenaline}",
        "timestamp": time.time()
    }
    
    # Convert event to dict AFTER using its attributes
    event_dict = top_event.to_dict()
    
    return InstinctResponse(
        event=event_dict,
        meaning={
            "significance_score": top_instinct.resonance_score,
            "context_label": f"{top_instinct.mode} Mode",
            "insight": "Reflex Arc" if top_instinct.triggers else "Analytical"
        },
        instinct={
            "reflex_arc": top_instinct.reflex_arc,
            "instinct_confidence": top_instinct.instinct_confidence,
            "adrenaline_level": top_instinct.adrenaline_level,
            "mode": top_instinct.mode,
            "triggers": [t.dict() for t in top_instinct.triggers]
        },
        signature=sig
    )
