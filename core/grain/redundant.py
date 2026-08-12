"""
Grain REDUNDANT tier — N-of-M signature survival (~30% damage tolerance).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.grain.exact import verify_exact
from core.grain.models import GrainConfig, GrainResult, GrainTier


def verify_redundant(
    events: List[Dict[str, Any]],
    expected_key_id: Optional[str] = None,
    config: Optional[GrainConfig] = None,
) -> GrainResult:
    """
    QR-like verification: cluster of signed events tolerates partial loss.
    Valid if valid_count / total >= (1 - damage_ratio).
    """
    config = config or GrainConfig()

    if len(events) < config.min_events:
        return GrainResult(
            tier_used=GrainTier.REDUNDANT,
            match_score=0.0,
            signal_to_noise=0.0,
            verdict="insufficient_signal",
            insufficient_signal=True,
            false_accept_risk=0.0,
            false_reject_risk=1.0,
            events_valid=0,
            events_total=len(events),
            min_tokens_required=config.min_events,
            insight=f"Need ≥{config.min_events} events for redundant tier; got {len(events)}.",
        )

    valid_count = 0
    resolved_key_id: Optional[str] = None
    for event in events:
        result = verify_exact(event, expected_key_id=expected_key_id)
        if result.verdict == "verified":
            valid_count += 1
            resolved_key_id = result.key_id

    total = len(events)
    survival_ratio = valid_count / total if total else 0.0
    required_ratio = 1.0 - config.damage_ratio
    match_score = survival_ratio

    if survival_ratio >= required_ratio:
        verdict = "verified" if valid_count == total else "likely_same_origin"
        insight = (
            f"{valid_count}/{total} signatures valid "
            f"(survival {survival_ratio:.0%} ≥ required {required_ratio:.0%})."
        )
    else:
        verdict = "rejected"
        insight = (
            f"{valid_count}/{total} signatures valid "
            f"(survival {survival_ratio:.0%} < required {required_ratio:.0%})."
        )

    snr = match_score / max(0.01, 1.0 - match_score)

    return GrainResult(
        tier_used=GrainTier.REDUNDANT,
        match_score=round(match_score, 4),
        signal_to_noise=round(snr, 4),
        verdict=verdict,
        false_accept_risk=round(max(0.0, 0.5 - survival_ratio), 4),
        false_reject_risk=round(max(0.0, required_ratio - survival_ratio), 4),
        events_valid=valid_count,
        events_total=total,
        key_id=resolved_key_id,
        insight=insight,
        meta={
            "survival_ratio": round(survival_ratio, 4),
            "required_ratio": round(required_ratio, 4),
            "damage_ratio": config.damage_ratio,
        },
    )
