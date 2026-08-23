from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
from core.prism import PrismEngine, PrismResult, ObserverContext
from core.echo import ResonanceEngine

from core.routing import ContentNegotiationRoute

router = APIRouter(
    prefix="/api/v2/prism",
    tags=["Prism (Cognitive)"],
    route_class=ContentNegotiationRoute,
)


class SynthesizeRequest(BaseModel):
    query: str
    """
    Either an event_id (direct seed) or a text query.
    If no event matches the id, the engine finds the closest matching event by text
    and uses it as the resonance seed.
    """
    identity_key: Optional[str] = None
    radius: float = 0.3
    limit: int = 20
    observer_context: Optional[ObserverContext] = None
    """
    The observer's personal meaning system.
    Defines which tokens are heavy, what categories exist, which resonance types matter.
    The same event means different things to different observers.
    The system does not decide — the observer does.

    Example:
    {
      "token_weights": {"father": 2.0, "war": -0.5, "home": 1.5},
      "vocabulary": {
        "grief":   ["gone", "empty", "quiet", "never"],
        "freedom": ["open", "air", "leaving", "finally"]
      },
      "harmonic_weights": {"emotional": 1.5, "cyclic": 2.0}
    }
    """


@router.post("/synthesize", response_model=PrismResult)
async def synthesize_meaning(payload: SynthesizeRequest, request: Request):
    """
    Cognitive Synthesis — the engine inhales the query, exhales meaning.

    Pipeline:
    1. **Seed resolution**: if `query` is an event_id, use it directly.
       If not found, fall back to text search — the top matching event becomes the seed.
    2. **Echo**: emit a resonance wave from the seed to find harmonically related memories.
    3. **Prism**: synthesize the resonance cloud into a primary meaning.

    Response includes the Perception Paradox fields:
    - `meaning` — primary reading (winner)
    - `alternative_readings` — competing readings, not discarded
    - `perception_gap` — 0.0 = clear single reading; 1.0 = maximum ambiguity
    - `is_paradoxical` — True when competing readings have near-equal weight but contradict
    - `has_unread_essence` — True when the seed event carries a blind_payload

    What you see (meaning) may not be what it is (alternative_readings).
    """
    indb = getattr(request.app.state, "indb", None)
    if not indb:
        raise HTTPException(status_code=503, detail="INDB Core not ready")

    echo_engine = ResonanceEngine(indb)
    prism_engine = PrismEngine(indb)

    # Step 1: Resolve seed — try event_id first, fall back to text search
    seed_id = payload.query
    seed = indb.get_event(seed_id)

    if not seed:
        # Text fallback: scan for the closest matching event
        query_lower = payload.query.lower()
        query_tokens = set(query_lower.split())
        best_score = 0.0
        best_event = None

        for event in indb.iter_events():
            event_tokens = set(t.lower() for t in event.raw_data_anchor)
            overlap = len(query_tokens & event_tokens)
            loc_match = any(qt in event.location.lower() for qt in query_tokens)
            score = float(overlap) + (0.5 if loc_match else 0.0)
            if score > best_score:
                best_score = score
                best_event = event

        if not best_event:
            raise HTTPException(
                status_code=404,
                detail="No matching event found. Inhale some events first."
            )
        seed_id = best_event.id

    # Step 2: Echo resonance cloud
    cloud = await echo_engine.resonate(
        seed_event_id=seed_id,
        radius=payload.radius,
        limit=payload.limit
    )

    if not cloud:
        raise HTTPException(
            status_code=404,
            detail="No resonance found. The memory is silent."
        )

    # Step 3: Prism synthesis — relational meaning, paradox-aware
    result = prism_engine.synthesize(
        query=payload.query,
        identity_key=payload.identity_key,
        resonance_cloud=cloud,
        observer=payload.observer_context,
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Prism could not crystallize a result."
        )

    return result
