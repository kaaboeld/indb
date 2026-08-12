"""
Grain — verification models.

Unified noise-tolerance spectrum: exact → redundant → resonant → statistical.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class GrainTier(str, Enum):
    """Verification tier ordered from strict (binary) to flexible (statistical)."""

    EXACT = "exact"              # Ed25519 / hash — ~0% tolerance (barcode)
    REDUNDANT = "redundant"      # N-of-M signatures — ~30% damage (QR)
    RESONANT = "resonant"        # Echo + reputation + FAR/FRR — ~30–50% (signature)
    STATISTICAL = "statistical"  # Token distribution p-value — floating (SynthID-like)


GrainTierInput = Union[GrainTier, Literal["auto"]]


class GrainConfig(BaseModel):
    """Tunable verification parameters."""

    tier: GrainTierInput = "auto"
    tolerance: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="FAR/FRR knob: 0=strict (high false reject), 1=permissive (high false accept)",
    )
    min_tokens: int = Field(
        default=20,
        ge=1,
        description="Minimum token count for statistical tier",
    )
    min_events: int = Field(
        default=3,
        ge=1,
        description="Minimum events for redundant / statistical cluster checks",
    )
    damage_ratio: float = Field(
        default=0.30,
        ge=0.0,
        le=1.0,
        description="Max tolerated damage ratio for redundant tier (QR Level H ≈ 0.30)",
    )


class GrainResult(BaseModel):
    """Outcome of a Grain verification pass."""

    tier_used: GrainTier
    match_score: float = Field(ge=0.0, le=1.0)
    p_value: Optional[float] = None
    signal_to_noise: float = 0.0
    verdict: Literal[
        "verified",
        "likely_same_origin",
        "insufficient_signal",
        "rejected",
    ]
    false_accept_risk: float = Field(ge=0.0, le=1.0)
    false_reject_risk: float = Field(ge=0.0, le=1.0)
    insufficient_signal: bool = False
    tokens_observed: int = 0
    min_tokens_required: int = 0
    events_valid: Optional[int] = None
    events_total: Optional[int] = None
    key_id: Optional[str] = None
    insight: str = ""
    meta: Dict[str, Any] = Field(default_factory=dict)


class TierInfo(BaseModel):
    """Description of one tier on the noise-tolerance axis."""

    tier: GrainTier
    label: str
    noise_tolerance: str
    description: str
    analogy: str


TIER_CATALOG: List[TierInfo] = [
    TierInfo(
        tier=GrainTier.EXACT,
        label="Exact",
        noise_tolerance="~0–5%",
        description="Ed25519 signature or key_id match. Binary: verified or rejected.",
        analogy="Barcode (EAN-13)",
    ),
    TierInfo(
        tier=GrainTier.REDUNDANT,
        label="Redundant",
        noise_tolerance="~30%",
        description="N-of-M signed events survive partial damage or export loss.",
        analogy="QR code (Reed–Solomon Level H)",
    ),
    TierInfo(
        tier=GrainTier.RESONANT,
        label="Resonant",
        noise_tolerance="~30–50%",
        description="Harmonic similarity weighted by source reputation. FAR/FRR via tolerance knob.",
        analogy="Handwritten signature biometrics",
    ),
    TierInfo(
        tier=GrainTier.STATISTICAL,
        label="Statistical",
        noise_tolerance="floating (p-value)",
        description="Token n-gram distribution vs reference cluster. Length-dependent signal.",
        analogy="SynthID / text watermark",
    ),
]
