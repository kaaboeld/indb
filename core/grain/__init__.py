"""
Grain — identity verification across the noise-tolerance spectrum.

Inhale identity. Tolerate noise. Verify the grain.
"""

from core.grain.engine import GrainEngine
from core.grain.models import GrainConfig, GrainResult, GrainTier, TIER_CATALOG

__all__ = [
    "GrainEngine",
    "GrainConfig",
    "GrainResult",
    "GrainTier",
    "TIER_CATALOG",
]
