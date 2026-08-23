"""
API endpoints for Contextual Lens queries
"""
from fastapi import APIRouter, Depends
from typing import Dict, Any
import uuid

from core.lens import ContextualLens, LensQueryEngine, LensMode
from core.deps import IndbDep
from core.kernel import AuthContext
from auth.flexible_auth import require_auth

async def get_auth(auth_info: dict = Depends(require_auth)) -> AuthContext:
    return AuthContext(
        user_id=auth_info.get("user_id", "api_user"),
        auth_method=auth_info.get("method", "api_key")
    )

from core.routing import ContentNegotiationRoute

router = APIRouter(prefix="/api/v2/lens", tags=["lens"], route_class=ContentNegotiationRoute)


@router.post("/query")
async def query_through_lens(
    request: Dict[str, Any],
    db: IndbDep,
    auth: AuthContext = Depends(get_auth),
) -> Dict[str, Any]:
    """
    Query data through Contextual Lens
    
    The lens creates a "Third Half" - a virtual 50% view formed by
    blending two contexts with adjustable ratios.
    
    Request Body:
    {
        "context_a": "recent",           // First context (H1)
        "context_b": "historical",       // Second context (H2)
        "ratio": [0.3, 0.7],            // Blend ratio (30% H1, 70% H2)
        "offset": 0.5,                  // Lens position (0.0 to 1.0)
        "zoom": 1.0,                    // Cognitive zoom (0.1 = child, 10.0 = adult)
        "mode": "sharp",                // Focus mode: sharp, deep, wide
        "refraction": 1.0,              // Subjective interpretation weight
        "limit": 100                    // Max events in lens view
    }
    
    Available contexts:
    - "recent": Events from last 24 hours
    - "historical": Events older than 24 hours
    - "high_frequency": Complex events (>5 tokens)
    - "simple": Simple events (<=5 tokens)
    - "all": All events
    
    Ratio examples:
    - [0.1, 0.9]: Heavy bias toward context B (10/90)
    - [0.3, 0.7]: Moderate blend (30/70)
    - [0.5, 0.5]: Equal balance (50/50)
    - [0.7, 0.3]: Moderate blend (70/30)
    - [0.9, 0.1]: Heavy bias toward context A (90/10)
    
    Response:
    {
        "status": "success",
        "data": {
            "h1_events": [...],      // Events from context A
            "h2_events": [...],      // Events from context B
            "lens_view": [...],      // Blended "Third Half"
            "metadata": {
                "h1_weight": 0.3,
                "h2_weight": 0.7,
                "h1_count": 30,
                "h2_count": 70,
                "lens_count": 50,    // 50% of total (The Third Half)
                "zoom": 1.0,
                "mode": "sharp",
                "offset": 0.5
            }
        }
    }
    """
    try:
        # Parse ratio
        ratio_raw = request.get("ratio", [0.5, 0.5])
        if not isinstance(ratio_raw, list) or len(ratio_raw) != 2:
            return {
                "status": "error",
                "message": "Ratio must be array of 2 numbers"
            }
        
        # Parse mode
        mode_str = request.get("mode", "sharp")
        try:
            mode = LensMode(mode_str)
        except ValueError:
            return {
                "status": "error",
                "message": f"Invalid mode: {mode_str}. Use: sharp, deep, or wide"
            }
        
        # Create lens
        lens = ContextualLens(
            id=str(uuid.uuid4()),
            context_a=request.get("context_a", "recent"),
            context_b=request.get("context_b", "historical"),
            ratio=tuple(ratio_raw),
            offset=request.get("offset", 0.5),
            zoom=request.get("zoom", 1.0),
            refraction=request.get("refraction", 1.0),
            mode=mode,
        )
        
        # Validate
        lens.validate_ratio()
        
        # Execute query
        engine = LensQueryEngine(db.db)
        result = engine.render(lens, limit=request.get("limit", 100))
        
        # Add lens config to response
        result["lens_config"] = lens.to_dict()
        
        return {
            "status": "success",
            "data": result
        }
        
    except ValueError as e:
        return {
            "status": "error",
            "message": str(e)
        }
    except Exception as e:
        print(f"Lens query error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"Internal error: {str(e)}"
        }


@router.post("/shift")
async def shift_lens_spectrum(
    request: Dict[str, Any],
    db: IndbDep,
    auth: AuthContext = Depends(get_auth),
) -> Dict[str, Any]:
    """
    Dynamically shift lens spectrum
    
    Adjusts the blend ratio between two contexts.
    
    Request Body:
    {
        "context_a": "recent",
        "context_b": "historical",
        "new_ratio": [0.1, 0.9],    // Shift to 10/90
        "new_offset": 0.2,
        "limit": 100
    }
    
    Response:
    Same as /query endpoint
    """
    try:
        # Parse new ratio
        new_ratio = request.get("new_ratio", [0.5, 0.5])
        if not isinstance(new_ratio, list) or len(new_ratio) != 2:
            return {
                "status": "error",
                "message": "new_ratio must be array of 2 numbers"
            }
        
        # Create shifted lens
        lens = ContextualLens(
            id=str(uuid.uuid4()),
            context_a=request.get("context_a", "recent"),
            context_b=request.get("context_b", "historical"),
            ratio=tuple(new_ratio),
            offset=request.get("new_offset", 0.5),
            zoom=request.get("zoom", 1.0),
            refraction=request.get("refraction", 1.0),
            mode=LensMode(request.get("mode", "sharp")),
        )
        
        lens.validate_ratio()
        
        # Execute query with shifted lens
        engine = LensQueryEngine(db.db)
        result = engine.render(lens, limit=request.get("limit", 100))
        
        result["lens_config"] = lens.to_dict()
        
        return {
            "status": "success",
            "data": result,
            "message": f"Lens shifted to {new_ratio[0]:.0%}/{new_ratio[1]:.0%}"
        }
        
    except Exception as e:
        print(f"Lens shift error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }
