"""
Instinct Module - Adrenaline-Based Instinctive Resonance

"Instinct is high-speed pattern matching where specific markers 
(Identity, Location, Key Tokens) override general logical consistency."

Modes:
- Analytical (adrenaline=0.0): Balanced weights, logical reasoning
- Alert (adrenaline=0.3-0.5): Moderate bias toward identity/location
- Instinctive (adrenaline=0.7-1.0): Extreme focus on personal markers
"""

from typing import List, Tuple, Optional
from pydantic import BaseModel
from core.event import Event
from core.echo import HarmonicWeights

class ReflexTrigger(BaseModel):
    """A reflex trigger that fired during instinct calculation"""
    type: str           # "owner", "location", "critical_token"
    bonus: float        # Bonus added to resonance
    reason: str         # Human-readable explanation

class InstinctResult(BaseModel):
    """Result of instinct-based resonance calculation"""
    event_id: str
    resonance_score: float
    reflex_arc: List[str]           # Trace of why instinct fired
    instinct_confidence: float      # How visceral the connection is (0-1)
    adrenaline_level: float         # Intensity used
    mode: str                       # "Analytical", "Alert", or "Instinctive"
    triggers: List[ReflexTrigger]   # Detailed trigger breakdown

# Critical tokens that trigger instinctive reactions
CRITICAL_TOKENS = {
    "danger", "urgent", "critical", "emergency", "warning",
    "threat", "immediate", "alert", "crisis", "panic"
}

def apply_adrenaline(base_weights: HarmonicWeights, intensity: float) -> HarmonicWeights:
    """
    Apply adrenaline shift to harmonic weights.
    
    As intensity increases (0.0 to 1.0):
    - Meta weight grows exponentially (identity/location bias)
    - Token weight decreases linearly (ignore lexical noise)
    - Emotion weight unchanged
    
    Args:
        base_weights: Starting weights (typically token=0.2, emotion=0.3, meta=0.5)
        intensity: Adrenaline level (0.0 = analytical, 1.0 = pure instinct)
    
    Returns:
        Adjusted weights for instinctive mode
    """
    if intensity <= 0:
        return base_weights
    
    # Non-linear shift (exponential for meta, linear for token)
    meta_boost = (intensity ** 1.5) * 0.4      # 0.0 to 0.4
    token_penalty = intensity * 0.15           # 0.0 to 0.15
    
    return HarmonicWeights(
        token=max(0.05, base_weights.token - token_penalty),
        emotion=base_weights.emotion,  # Unchanged
        meta=min(0.9, base_weights.meta + meta_boost)
    )

def detect_reflex_triggers(
    seed: Event, 
    target: Event, 
    adrenaline: float
) -> Tuple[float, List[ReflexTrigger]]:
    """
    Detect reflex triggers and calculate bonus.
    
    Priority hierarchy:
    1. Owner Signature (source_id match): +0.8 * adrenaline
    2. Location Match: +0.7 * adrenaline
    3. Critical Token Match: +0.5 * adrenaline
    
    Args:
        seed: Source event
        target: Target event to compare
        adrenaline: Intensity (0.0-1.0)
    
    Returns:
        (total_bonus, list_of_triggers)
    """
    triggers = []
    total_bonus = 0.0
    
    # 1. Owner/Identity Match (Highest Priority)
    if seed.source_id and target.source_id and seed.source_id == target.source_id:
        if adrenaline > 0.3:  # Only fire in alert/instinctive mode
            bonus = 0.8 * adrenaline
            total_bonus += bonus
            triggers.append(ReflexTrigger(
                type="owner",
                bonus=bonus,
                reason=f"Owner Signature Match: {seed.source_id}"
            ))
    
    # 2. Location Match (Territorial Reflex)
    if seed.location == target.location:
        bonus = 0.7 * adrenaline
        total_bonus += bonus
        triggers.append(ReflexTrigger(
            type="location",
            bonus=bonus,
            reason=f"Location Match: {seed.location}"
        ))
    
    # 3. Critical Token Match (Moment Reflex)
    seed_tokens = set(seed.raw_data_anchor)
    target_tokens = set(target.raw_data_anchor)
    shared_critical = seed_tokens & target_tokens & CRITICAL_TOKENS
    
    if shared_critical:
        bonus = 0.5 * adrenaline
        total_bonus += bonus
        triggers.append(ReflexTrigger(
            type="critical_token",
            bonus=bonus,
            reason=f"Critical Tokens: {', '.join(shared_critical)}"
        ))
    
    return total_bonus, triggers

def calculate_instinct_confidence(
    reflex_bonus: float,
    adrenaline: float,
    location_match: bool
) -> float:
    """
    Calculate how "visceral" the instinctive connection is.
    
    Formula:
    - 60% from reflex strength
    - 30% from adrenaline intensity
    - 10% from territorial bias
    
    Interpretation:
    - 0.0-0.3: Weak instinct (analytical override)
    - 0.3-0.6: Moderate instinct (alert state)
    - 0.6-1.0: Strong instinct (pure reflex)
    """
    confidence = (
        (reflex_bonus * 0.6) +
        (adrenaline * 0.3) +
        (0.1 if location_match else 0.0)
    )
    return min(1.0, confidence)

def get_instinct_mode(adrenaline: float) -> str:
    """Determine instinct mode based on adrenaline level"""
    if adrenaline < 0.3:
        return "Analytical"
    elif adrenaline < 0.7:
        return "Alert"
    else:
        return "Instinctive"

def calculate_instinct_resonance(
    seed: Event,
    target: Event,
    base_resonance_score: float,
    adrenaline: float = 0.5
) -> InstinctResult:
    """
    Calculate instinct-enhanced resonance.
    
    Combines:
    1. Base resonance score (from Echo with adjusted weights)
    2. Reflex bonuses (from pattern triggers)
    3. Instinct confidence (visceral connection strength)
    
    Args:
        seed: Source event
        target: Target event
        base_resonance_score: Score from Echo (with adrenaline-adjusted weights)
        adrenaline: Intensity (0.0-1.0)
    
    Returns:
        InstinctResult with full trace
    """
    # Detect reflex triggers
    reflex_bonus, triggers = detect_reflex_triggers(seed, target, adrenaline)
    
    # Calculate final resonance
    final_score = min(1.0, base_resonance_score + reflex_bonus)
    
    # Calculate instinct confidence
    location_match = seed.location == target.location
    confidence = calculate_instinct_confidence(reflex_bonus, adrenaline, location_match)
    
    # Build reflex arc trace
    reflex_arc = [t.reason for t in triggers]
    if not reflex_arc:
        reflex_arc = ["No reflex triggers (analytical mode)"]
    
    return InstinctResult(
        event_id=target.id,
        resonance_score=final_score,
        reflex_arc=reflex_arc,
        instinct_confidence=confidence,
        adrenaline_level=adrenaline,
        mode=get_instinct_mode(adrenaline),
        triggers=triggers
    )
