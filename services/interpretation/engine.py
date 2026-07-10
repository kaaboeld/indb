import time
from typing import Dict, Any, List, Optional
from core.event import Event
from core.cache import TTLCache
from core.constants import (
    INTERPRET_MOOD_DEFAULT,
    INTERPRET_ACTIVATION_BASELINE,
    INTERPRET_ACTIVATION_LOCATION_MATCH,
    INTERPRET_ACTIVATION_TEMPORAL_FRESH,
    INTERPRET_ACTIVATION_RESONANCE,
    INTERPRET_TEMPORAL_OPACITY_THRESHOLD,
    INTERPRET_TEMPORAL_DECAY_FACTOR,
    INTERPRET_EMPTY_ID,
    INTERPRET_EMPTY_LOCATION,
    INTERPRET_EMPTY_TIMESTAMP,
    INTERPRET_FIREWALL_BLOCKED_EMOTION,
    INTERPRET_BLOCKED_ACTIVATION,
    INTERPRET_FIREWALL_REASON_DEFAULT,
    INTERPRET_TOKEN_NEGATIVE,
    INTERPRET_TOKEN_POSITIVE,
    INTERPRET_TOKEN_HIGH_ENERGY,
    INTERPRET_CACHE_TTL_SEC,
)
from services.interpretation.cognitive_firewall import CognitiveFirewall


class JITRenderer:
    """
    The JIT Renderer v3.0 (True Abstract Interpretation).
    Decoupled from Storage (INDB).
    """

    def __init__(self, cache: TTLCache, firewall: CognitiveFirewall):
        self.cache = cache
        self.firewall = firewall

    def _get_attr(self, obj: Any, attr: str, default: Any = None) -> Any:
        """Safe attribute access for Event, FusedEvent, or dict."""
        if isinstance(obj, dict):
            return obj.get(attr, default)
        return getattr(obj, attr, default)

    def render(self, event: Event, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Input: Abstract Token Vector (e.g. ["fast", "loud", "heartbeat"]) + Context
        Output: Meaning/Emotion/Narrative (Derived purely at runtime)
        """
        g = lambda attr, d=None: self._get_attr(event, attr, d)
        mood = context.get("mood", INTERPRET_MOOD_DEFAULT)
        current_location = context.get("location", g("location", INTERPRET_EMPTY_LOCATION))
        
        # Check Cache
        cache_key = f"{g('id', INTERPRET_EMPTY_ID)}:{mood}:{current_location}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        # 1. Analyze Tokens (Latent Potential)
        # Apply Cognitive Firewall
        decision = self.firewall.inspect(event, context)
        
        if not decision["allowed"]:
            # Short-circuit return for blocked memories
            reason = decision.get("reason", INTERPRET_FIREWALL_REASON_DEFAULT)
            return {
                "id": g("id", INTERPRET_EMPTY_ID),
                "timestamp": g("timestamp", INTERPRET_EMPTY_TIMESTAMP),
                "raw_data_anchor": [],  # Redacted by firewall
                "location": g("location", INTERPRET_EMPTY_LOCATION),
                "original_location": g("location", INTERPRET_EMPTY_LOCATION),
                "derived_emotion": INTERPRET_FIREWALL_BLOCKED_EMOTION,
                "context": context,
                "interpretation": {
                    "narrative": f"[BLOCKED] {reason}",
                    "emotional_weight": INTERPRET_BLOCKED_ACTIVATION,
                    "tokens": [],
                },
                "activation_score": INTERPRET_BLOCKED_ACTIVATION,
                "firewall_status": INTERPRET_FIREWALL_BLOCKED_EMOTION,
                "is_fused": g("is_fused", bool(g("fusion_count", 0) > 1)),
                "fusion_count": g("fusion_count", 0)
            }
        
        active_event = decision.get("event", event)
        # Helper to get attribute safely
        def get_attr(obj, attr, default):
            if isinstance(obj, dict):
                return obj.get(attr, default)
            return getattr(obj, attr, default)
            
        filtered_tokens = get_attr(active_event, "raw_data_anchor", [])

        # 2. Derive Meaning based on Context (input: mood, tokens → output: emotion, narrative)
        derived_emotion = INTERPRET_MOOD_DEFAULT
        derived_narrative = ""

        # Calculate time distance (input: event.timestamp → output: temporal_opacity)
        ts = g("timestamp", None)
        age_hours = (time.time() - (ts if ts is not None else time.time())) / 3600.0
        temporal_opacity = 1.0 / (1.0 + (age_hours * INTERPRET_TEMPORAL_DECAY_FACTOR))

        # Analyze token characteristics
        token_profile = self._analyze_tokens(filtered_tokens)
        
        # --- INTERPRETATION MATRIX ---

        loc = g("location", INTERPRET_EMPTY_LOCATION)
        tokens = g("raw_data_anchor", []) or filtered_tokens
        tok0 = tokens[0] if tokens else INTERPRET_EMPTY_LOCATION
        if mood == "High_Value":
            # Optimistic/Growth mindset looks for Logic, Energy, and Opportunity
            if token_profile["energy"] == "high":
                derived_emotion = "Joy"
                derived_narrative = f"The energy from {loc} ({', '.join(tokens)}) fuels my current momentum."
            elif token_profile["valance"] == "negative":  # Pain/Danger
                derived_emotion = "Curiosity"  # Reframe negative as lesson
                derived_narrative = f"Analyzing past resistance in {loc}. The {tok0} indicates a boundary I can now cross."
            else:
                derived_emotion = "Focus"
                derived_narrative = f"Extracting utility from {loc} data stream."

        elif mood == "Fear":
            # Pessimistic/Survival mindset looks for Threats and Pain
            if token_profile["valance"] == "negative" or token_profile["energy"] == "high":
                derived_emotion = "Fear"  # Even high energy feels like threat
                derived_narrative = f"THREAT DETECTED in {loc}. The {tok0} signals immediate danger."
            elif token_profile["valance"] == "positive":
                derived_emotion = "Anxiety"  # Good things feel suspicious
                derived_narrative = f"The {', '.join(tokens)} in {loc} feels deceptive. Is it a trap?"
            else:
                derived_emotion = "Paranoia"
                derived_narrative = (
                    f"Unknown signals from {loc}. Scanning for hidden vectors."
                )

        else:  # Neutral or unknown mood
            derived_emotion = INTERPRET_MOOD_DEFAULT
            derived_narrative = (
                f"Retrieved data point from {loc}: {', '.join(filtered_tokens)}."
            )

        # 3. Calculate Activation (input: location match, temporal_opacity, mood resonance → output: score)
        activation_score = INTERPRET_ACTIVATION_BASELINE
        if current_location == loc:
            activation_score += INTERPRET_ACTIVATION_LOCATION_MATCH
        if temporal_opacity > INTERPRET_TEMPORAL_OPACITY_THRESHOLD:
            activation_score += INTERPRET_ACTIVATION_TEMPORAL_FRESH
        if derived_emotion == mood:
            activation_score += INTERPRET_ACTIVATION_RESONANCE

        result = {
            "id": g("id", INTERPRET_EMPTY_ID),
            "timestamp": g("timestamp", INTERPRET_EMPTY_TIMESTAMP),
            "raw_data_anchor": tokens,
            "location": loc,
            "ttl": g("ttl"),
            "blind_payload": g("blind_payload"),
            "original_location": loc,
            "derived_emotion": derived_emotion,
            "context": context,
            "interpretation": {
                "narrative": derived_narrative,
                "emotional_weight": round(activation_score, 2),
                "tokens": filtered_tokens,
            },
            "activation_score": round(min(activation_score, 1.0), 2),
            "firewall_status": "ALLOWED" if filtered_tokens == tokens else "REDACTED",
            "is_fused": g("is_fused", bool(g("fusion_count", 0) > 1)),
            "fusion_count": g("fusion_count", 0)
        }

        # Cache Result
        self.cache.set(cache_key, result, ttl=INTERPRET_CACHE_TTL_SEC)

        return result

    def _analyze_tokens(self, tokens: List[str]) -> Dict[str, Any]:
        """Classify raw tokens into latent characteristics (input: raw_data_anchor → output: profile)."""
        score = 0
        energy = "low"

        for t in tokens:
            t_lower = str(t).lower()
            if any(s in t_lower for s in INTERPRET_TOKEN_NEGATIVE):
                score -= 1
            if any(s in t_lower for s in INTERPRET_TOKEN_POSITIVE):
                score += 1
            if any(s in t_lower for s in INTERPRET_TOKEN_HIGH_ENERGY):
                energy = "high"

        return {
            "valance": "positive" if score > 0 else "negative" if score < 0 else "neutral",
            "energy": energy,
        }
