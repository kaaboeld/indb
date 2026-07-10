"""
Cognitive pipeline — Subwave (unified frequency) then Slice (what-if shift).

Anchor → broadcast lock frame → horizontal rescoring → optional Prism.
No LLM.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from core.constants import (
    SUBWAVE_LOCK_THRESHOLD,
    SUBWAVE_MAX_NODES,
    WHAT_IF_SUBWAVE_DEFAULT,
)
from core.context_slice import ContextSliceEngine, ContextSliceResult
from core.prism import ObserverContext
from core.seed_resolver import SeedResolution
from core.subwave import SubwaveEngine, SubwaveResult


class CoreCognitiveResult(BaseModel):
    """Full core path: subwave lock frame + contextual slice."""
    subwave: Optional[SubwaveResult] = None
    slice: ContextSliceResult


async def run_subwave_then_slice(
    indb,
    *,
    seed_id: str = "",
    query: Optional[str] = None,
    what_if: str,
    observer: Optional[ObserverContext] = None,
    radius: float = 0.3,
    slice_limit: int = 20,
    subwave_limit: int = SUBWAVE_MAX_NODES,
    lock_threshold: float = SUBWAVE_LOCK_THRESHOLD,
    use_subwave: bool = WHAT_IF_SUBWAVE_DEFAULT,
) -> CoreCognitiveResult:
    """
    1. Subwave — tune horizontal neighbors to one frequency (modifier).
    2. Slice — Echo cloud + factor shift + Prism overlay on the same anchor.
    """
    subwave_out: Optional[SubwaveResult] = None
    if use_subwave:
        subwave_out = await SubwaveEngine(indb).broadcast(
            seed_id=seed_id,
            query=query,
            modifier=what_if,
            radius=radius,
            limit=subwave_limit,
            lock_threshold=lock_threshold,
        )
        if subwave_out.anchor.anchor_id and not seed_id:
            seed_id = subwave_out.anchor.anchor_id

    slice_out = await ContextSliceEngine(indb).slice(
        seed_id=seed_id,
        what_if=what_if,
        radius=radius,
        limit=slice_limit,
        observer=observer,
        query=query,
    )

    if subwave_out:
        slice_out.logic = (
            f"Subwave: coherence={subwave_out.coherence}, "
            f"locked={subwave_out.nodes_locked}/{subwave_out.nodes_tuned}, "
            f"mode={subwave_out.scan_mode}\n"
            + slice_out.logic
        )

    return CoreCognitiveResult(subwave=subwave_out, slice=slice_out)


async def run_from_resolution(
    indb,
    resolution: SeedResolution,
    what_if: str,
    observer: Optional[ObserverContext] = None,
    radius: float = 0.3,
    limit: int = 20,
    use_subwave: bool = WHAT_IF_SUBWAVE_DEFAULT,
) -> CoreCognitiveResult:
    if not resolution.resolved:
        raise ValueError("Cannot run pipeline: seed not resolved")
    return await run_subwave_then_slice(
        indb,
        seed_id=resolution.seed_id or "",
        query=resolution.query,
        what_if=what_if,
        observer=observer,
        radius=radius,
        slice_limit=limit,
        use_subwave=use_subwave,
    )
