"""
Grain RESONANT tier — Echo + reputation with FAR/FRR tolerance (~30–50%).
"""

from __future__ import annotations

from typing import Optional

from core.echo import ResonanceEngine
from core.event import Event
from core.grain.models import GrainConfig, GrainResult, GrainTier


def _threshold(config: GrainConfig) -> float:
    """Map tolerance knob to acceptance threshold (strict → permissive)."""
    return 0.70 - config.tolerance * 0.40


def _estimate_far(score: float, config: GrainConfig) -> float:
    """Heuristic false-accept risk — rises as tolerance and score increase."""
    base = max(0.0, score - _threshold(config))
    return min(1.0, base * (0.5 + config.tolerance * 0.5))


def _estimate_frr(score: float, config: GrainConfig) -> float:
    """Heuristic false-reject risk — rises when score is below threshold."""
    gap = max(0.0, _threshold(config) - score)
    return min(1.0, gap * (1.5 - config.tolerance * 0.5))


def verify_resonant(
    reference: Event,
    candidate: Event,
    echo_engine: ResonanceEngine,
    reputation: float = 0.5,
    config: Optional[GrainConfig] = None,
) -> GrainResult:
    """
    Signature-like verification: same hand, different surface (glass vs paper).
    Resonance × reputation, with adjustable FAR/FRR via tolerance.
    """
    config = config or GrainConfig()
    resonance = echo_engine.calculate_resonance(reference, candidate)
    rep = max(0.0, min(1.0, reputation))
    match_score = min(1.0, resonance * (0.5 + rep * 0.5))

    threshold = _threshold(config)
    tokens = candidate.raw_data_anchor or []

    if match_score >= threshold:
        verdict = "likely_same_origin"
        insight = (
            f"Resonance {resonance:.2f} × reputation {rep:.2f} "
            f"≥ threshold {threshold:.2f} — likely same origin."
        )
    else:
        verdict = "rejected"
        insight = (
            f"Resonance {resonance:.2f} × reputation {rep:.2f} "
            f"< threshold {threshold:.2f} — origin not confirmed."
        )

    snr = match_score / max(0.01, 1.0 - match_score)

    return GrainResult(
        tier_used=GrainTier.RESONANT,
        match_score=round(match_score, 4),
        signal_to_noise=round(snr, 4),
        verdict=verdict,
        false_accept_risk=round(_estimate_far(match_score, config), 4),
        false_reject_risk=round(_estimate_frr(match_score, config), 4),
        tokens_observed=len(tokens),
        insight=insight,
        meta={
            "resonance": round(resonance, 4),
            "reputation": rep,
            "threshold": round(threshold, 4),
            "reference_id": reference.id,
            "candidate_id": candidate.id,
        },
    )
