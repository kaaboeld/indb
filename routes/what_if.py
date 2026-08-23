"""
What-If API — base query + abstract modifier.

POST /api/v2/what-if
mode=core  → subwave broadcast + horizontal slice (no LLM)
mode=llm   → LLM narrative (Hermes required)
mode=both  → core pipeline + LLM
"""
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from core.cognitive_pipeline import run_from_resolution
from core.constants import (
    WHAT_IF_MODE_BOTH,
    WHAT_IF_MODE_CORE,
    WHAT_IF_MODE_LLM,
    WHAT_IF_RETRY_AFTER_SECONDS,
    WHAT_IF_SUBWAVE_DEFAULT,
)
from core.models import StandardResponse
from core.observer_profiles import resolve_observer
from core.prism import ObserverContext
from core.seed_resolver import resolve_seed
from services.sources.hermes.config import HermesConfig
from services.what_if.base_runner import run_base_query
from services.what_if.runner import run_what_if

from core.routing import ContentNegotiationRoute

router = APIRouter(
    prefix="/api/v2/what-if",
    tags=["What-If (Hypothetical)"],
    route_class=ContentNegotiationRoute,
)


class WhatIfRequest(BaseModel):
    base_query_type: Literal["interpret", "search", "echo", "prism", "deduction"]
    base_params: Dict[str, Any] = Field(default_factory=dict)
    what_if: str = Field(..., min_length=1)
    mode: Literal["core", "llm", "both"] = WHAT_IF_MODE_CORE
    observer_context: Optional[ObserverContext] = None
    observer_profile: Optional[str] = None
    radius: float = 0.3
    limit: int = 20
    use_subwave: bool = WHAT_IF_SUBWAVE_DEFAULT


@router.post("", response_model=StandardResponse[Dict[str, Any]])
async def what_if_prediction(payload: WhatIfRequest, request: Request):
    """
    What-If — any base API query + abstract «what if» modifier.

    - core: Subwave (unified frequency) + slice (factor shift + Prism)
    - llm: Hermes/Ollama narrative over base_result JSON
    - both: core pipeline + LLM prediction
    """
    if payload.mode in (WHAT_IF_MODE_LLM, WHAT_IF_MODE_BOTH):
        hermes = HermesConfig.from_env()
        if not hermes.enabled:
            raise HTTPException(
                status_code=503,
                detail="What-if LLM requires Hermes. Set HERMES_ENABLED=true or use mode=core.",
                headers={"Retry-After": str(WHAT_IF_RETRY_AFTER_SECONDS)},
            )

    indb = getattr(request.app.state, "indb", None)
    if not indb:
        raise HTTPException(status_code=503, detail="INDB Core not ready")

    try:
        observer = resolve_observer(payload.observer_profile, payload.observer_context)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        base_result = await run_base_query(indb, payload.base_query_type, payload.base_params)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    data: Dict[str, Any] = {
        "base_result": base_result,
        "what_if": payload.what_if,
        "mode": payload.mode,
    }

    if payload.mode in (WHAT_IF_MODE_CORE, WHAT_IF_MODE_BOTH):
        resolution = resolve_seed(payload.base_query_type, payload.base_params, base_result)
        data["seed_resolution"] = {
            "seed_id": resolution.seed_id,
            "query": resolution.query,
            "source": resolution.source,
        }
        if resolution.resolved:
            try:
                pipeline = await run_from_resolution(
                    indb,
                    resolution,
                    payload.what_if,
                    observer=observer,
                    radius=payload.radius,
                    limit=payload.limit,
                    use_subwave=payload.use_subwave,
                )
                data["subwave"] = (
                    pipeline.subwave.model_dump() if pipeline.subwave else None
                )
                data["slice"] = pipeline.slice.model_dump()
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        else:
            data["subwave"] = None
            data["slice"] = None
            data["slice_note"] = "Could not resolve seed from base query."

    if payload.mode in (WHAT_IF_MODE_LLM, WHAT_IF_MODE_BOTH):
        summary = _summarize_for_llm(base_result)
        if payload.mode == WHAT_IF_MODE_BOTH:
            if data.get("subwave"):
                summary += "\n\nSubwave locked: " + str(
                    data["subwave"].get("nodes_locked", 0)
                )
            if data.get("slice"):
                summary += "\n\n" + data["slice"].get("logic", "")
        data["prediction"] = run_what_if(summary, payload.what_if)

    return StandardResponse(data=data)


def _summarize_for_llm(data: Any) -> str:
    import json
    if isinstance(data, dict):
        s = json.dumps(data, ensure_ascii=False, default=str)
        return s[:2000] + ("..." if len(s) > 2000 else "")
    if isinstance(data, list):
        return json.dumps(data[:10], ensure_ascii=False, default=str)[:2000]
    return str(data)[:2000]
