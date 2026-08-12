"""
Grain EXACT tier — Ed25519 / key_id verification (~0% noise tolerance).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.grain.models import GrainResult, GrainTier
from core.signing import verify_event_signature


def verify_exact(event: Dict[str, Any], expected_key_id: Optional[str] = None) -> GrainResult:
    """
    Binary verification: signature valid or not.
    Unsigned events pass with verdict rejected unless explicitly allowed elsewhere.
    """
    valid, key_id, err = verify_event_signature(event)

    if not event.get("signature"):
        return GrainResult(
            tier_used=GrainTier.EXACT,
            match_score=0.0,
            signal_to_noise=0.0,
            verdict="rejected",
            false_accept_risk=0.0,
            false_reject_risk=1.0,
            insight="No signature present — exact tier requires Ed25519 proof.",
            meta={"error": "unsigned"},
        )

    if not valid:
        return GrainResult(
            tier_used=GrainTier.EXACT,
            match_score=0.0,
            signal_to_noise=0.0,
            verdict="rejected",
            false_accept_risk=0.0,
            false_reject_risk=0.0,
            key_id=key_id,
            insight=f"Signature invalid: {err}",
            meta={"error": err},
        )

    if expected_key_id and key_id != expected_key_id:
        return GrainResult(
            tier_used=GrainTier.EXACT,
            match_score=0.0,
            signal_to_noise=0.0,
            verdict="rejected",
            false_accept_risk=0.0,
            false_reject_risk=0.0,
            key_id=key_id,
            insight=f"key_id mismatch: expected {expected_key_id[:16]}…, got {key_id[:16]}…",
            meta={"expected_key_id": expected_key_id},
        )

    return GrainResult(
        tier_used=GrainTier.EXACT,
        match_score=1.0,
        signal_to_noise=99.0 if key_id else 0.0,
        verdict="verified",
        false_accept_risk=0.0,
        false_reject_risk=0.0,
        key_id=key_id,
        insight="Ed25519 signature verified — axiom-grade identity.",
    )
