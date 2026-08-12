"""
Grain STATISTICAL tier — token n-gram distribution fingerprint (SynthID-like).
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Dict, Iterable, List, Optional, Tuple

from core.event import Event
from core.grain.models import GrainConfig, GrainResult, GrainTier


def _ngrams(tokens: List[str], n: int = 2) -> Counter:
    """Build n-gram frequency counter from token list."""
    normalized = [t.lower().strip() for t in tokens if t and len(t.strip()) >= 2]
    if len(normalized) < n:
        return Counter()
    return Counter(
        tuple(normalized[i : i + n]) for i in range(len(normalized) - n + 1)
    )


def build_distribution(events: Iterable[Event], n: int = 2) -> Counter:
    """Aggregate n-gram distribution from a cluster of reference events."""
    combined: Counter = Counter()
    for event in events:
        combined.update(_ngrams(event.raw_data_anchor or [], n=n))
    return combined


def _chi_squared_p_value(
    observed: Counter,
    expected: Counter,
) -> Tuple[float, float]:
    """
    Compare observed n-gram counts to expected reference distribution.
    Returns (chi_squared_statistic, approximate_p_value).
    """
    if not observed or not expected:
        return 0.0, 1.0

    total_obs = sum(observed.values())
    total_exp = sum(expected.values())
    if total_obs == 0 or total_exp == 0:
        return 0.0, 1.0

    chi2 = 0.0
    all_keys = set(observed.keys()) | set(expected.keys())
    for key in all_keys:
        obs = observed.get(key, 0)
        exp_count = expected.get(key, 0)
        exp = (exp_count / total_exp) * total_obs
        if exp > 0:
            chi2 += (obs - exp) ** 2 / exp

    # Rough p-value from chi-squared with df ≈ len(all_keys) - 1
    df = max(1, len(all_keys) - 1)
    # Wilson-Hilferty normal approximation for upper tail
    z = ((chi2 / df) ** (1 / 3) - (1 - 2 / (9 * df))) / math.sqrt(2 / (9 * df))
    # One-sided: lower chi2 → higher p (better match)
    p_value = 0.5 * (1 + math.erf(z / math.sqrt(2)))
    return chi2, max(0.0, min(1.0, p_value))


def verify_statistical(
    reference_events: List[Event],
    candidate: Event,
    config: Optional[GrainConfig] = None,
) -> GrainResult:
    """
    Detect whether candidate tokens statistically match a reference cluster.
    Signal strength grows with token count — short texts cannot be verified.
    """
    config = config or GrainConfig()
    ref_tokens = sum(len(e.raw_data_anchor or []) for e in reference_events)
    cand_tokens = candidate.raw_data_anchor or []
    tokens_observed = len(cand_tokens)

    if ref_tokens < config.min_tokens:
        return GrainResult(
            tier_used=GrainTier.STATISTICAL,
            match_score=0.0,
            p_value=1.0,
            signal_to_noise=0.0,
            verdict="insufficient_signal",
            insufficient_signal=True,
            false_accept_risk=0.0,
            false_reject_risk=1.0,
            tokens_observed=tokens_observed,
            min_tokens_required=config.min_tokens,
            insight=(
                f"Reference cluster has {ref_tokens} tokens; "
                f"statistical tier needs ≥{config.min_tokens}."
            ),
        )

    if tokens_observed < max(5, config.min_tokens // 4):
        return GrainResult(
            tier_used=GrainTier.STATISTICAL,
            match_score=0.0,
            p_value=1.0,
            signal_to_noise=0.0,
            verdict="insufficient_signal",
            insufficient_signal=True,
            false_accept_risk=0.0,
            false_reject_risk=1.0,
            tokens_observed=tokens_observed,
            min_tokens_required=max(5, config.min_tokens // 4),
            insight=(
                f"Candidate has {tokens_observed} tokens — "
                "too short for statistical detection (SynthID noise floor)."
            ),
        )

    expected = build_distribution(reference_events)
    observed = _ngrams(cand_tokens)
    chi2, p_value = _chi_squared_p_value(observed, expected)

    # Higher p-value → distributions align → higher match
    match_score = p_value
    # Significance threshold shifts with tolerance (strict = high p required)
    p_threshold = 0.05 + (1.0 - config.tolerance) * 0.45

    if p_value >= p_threshold:
        verdict = "likely_same_origin"
        insight = (
            f"n-gram distribution aligns (p={p_value:.4f} ≥ {p_threshold:.4f}). "
            "Statistical fingerprint detected."
        )
    else:
        verdict = "rejected"
        insight = (
            f"n-gram distribution diverges (p={p_value:.4f} < {p_threshold:.4f}). "
            "Origin not confirmed at statistical tier."
        )

    snr = match_score / max(0.001, 1.0 - match_score)

    return GrainResult(
        tier_used=GrainTier.STATISTICAL,
        match_score=round(match_score, 4),
        p_value=round(p_value, 6),
        signal_to_noise=round(snr, 4),
        verdict=verdict,
        false_accept_risk=round(max(0.0, p_value - p_threshold + 0.1) * (1 - config.tolerance), 4),
        false_reject_risk=round(max(0.0, p_threshold - p_value), 4),
        insufficient_signal=False,
        tokens_observed=tokens_observed,
        min_tokens_required=config.min_tokens,
        insight=insight,
        meta={
            "chi_squared": round(chi2, 4),
            "p_threshold": round(p_threshold, 4),
            "reference_event_count": len(reference_events),
            "reference_token_count": ref_tokens,
        },
    )


def embed_watermark_bias(tokens: List[str], secret: bytes, strength: float = 0.15) -> List[str]:
    """
    Optional client/connector helper: lightly bias token ordering toward a secret seed.
    Not applied automatically — source connectors may call this at transform time.
    """
    if not tokens or not secret:
        return tokens
    seed = int.from_bytes(secret[:8].ljust(8, b"\0"), "big")
    scored = sorted(
        enumerate(tokens),
        key=lambda pair: (hash((pair[1].lower(), seed + pair[0])) % 1000, pair[0]),
    )
    nudge = max(1, int(len(tokens) * strength))
    head = [t for _, t in scored[:nudge]]
    tail = [t for _, t in scored[nudge:]]
    return head + tail
