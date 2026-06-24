"""
Prism Engine (Cognitive Synthesizer)
"Transforms Data + Resonance into Meaning"

Formula:
S_score = (Mass * Resonance) * Identity_Alignment * Personal_Weight

Perception Paradox:
When two competing interpretations of the same event carry similar weight but point
in different directions, the system does NOT resolve the contradiction — it surfaces it.
perception_gap → 1.0 means: what you see may not be what it is.

Relational Meaning:
Meaning is not a property of the event.
It is a property of the relationship between the event and the observer.
The same tokens mean different things to different observers.
The system does not decide what is "life" or "death", "good" or "bad".
The observer's context defines the weight and label.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel
import math

from core.event import Event
from core.echo import ResonanceResult
from core.models import EventResponse
from core.constants import (
    PRISM_ALIGNMENT_OWNER,
    PRISM_ALIGNMENT_TOKEN_MATCH,
    PRISM_ALIGNMENT_DEFAULT,
    PRISM_ALIGNMENT_ANONYMOUS,
    PRISM_MASS_BASE,
    PRISM_MASS_COLLECTIVE_THRESHOLD,
    PRISM_INSIGHT_DEEPLY_PERSONAL_ALIGNMENT,
    PRISM_PERSONAL_WEIGHT_RESONANCE_THRESHOLD,
    PRISM_PERSONAL_WEIGHT_MIN,
    PRISM_PARADOX_SCORE_PROXIMITY_THRESHOLD,
    PRISM_PARADOX_MIN_CANDIDATES,
    PRISM_LABEL_SUBJECTIVE,
    PRISM_LABEL_OBJECTIVE,
    PRISM_INSIGHT_DEEPLY_PERSONAL,
    PRISM_INSIGHT_COLLECTIVE_TRUTH,
    PRISM_INSIGHT_DIRECT_HIT,
    PRISM_INSIGHT_EMOTIONAL_MATCH,
    PRISM_INSIGHT_TIME_ECHO,
)


class ObserverContext(BaseModel):
    """
    The observer's personal meaning system.

    The system does not impose labels. The observer defines what things mean
    through their own vocabulary, weights, and token resonances.

    All fields are optional — if not provided, the system falls back to neutral defaults.
    """
    # Token weights: tokens that carry personal significance
    # e.g. {"father": 2.0, "home": 1.5, "war": -0.5}
    # Negative weight = this token reduces significance for this observer
    token_weights: Dict[str, float] = {}

    # Personal vocabulary: how the observer categorizes experience
    # e.g. {"freedom": ["open", "air", "leaving"], "loss": ["gone", "empty", "quiet"]}
    # When event tokens match a category, that category name becomes the context_label
    vocabulary: Dict[str, List[str]] = {}

    # Harmonic type weights — which resonance types matter more to this observer
    # e.g. {"emotional": 1.5, "cyclic": 2.0, "direct": 0.8}
    harmonic_weights: Dict[str, float] = {}


class MeaningVector(BaseModel):
    significance_score: float
    context_label: str       # Observer-defined or default: "Personal" / "Shared" / "Distant"
    insight: str             # What the system noticed about this reading


class PrismResult(BaseModel):
    event: EventResponse
    meaning: MeaningVector

    # Perception Paradox fields
    # When is_paradoxical is True: the top interpretation and the alternatives are in tension.
    # The system saw something and interpreted it — but there is a competing reading of equal weight.
    # What you see (meaning) may not correspond to what it is (alternative_readings).
    alternative_readings: List[MeaningVector] = []
    is_paradoxical: bool = False
    perception_gap: float = 0.0  # 0.0 = clear single reading; 1.0 = maximum perceptual ambiguity

    # True when the event carries a blind_payload: the engine interprets the anchor,
    # but the actual essence is unread. The interpretation may not match the reality inside.
    has_unread_essence: bool = False


class PrismEngine:
    def __init__(self, indb_instance=None):
        self.indb = indb_instance

    def calculate_identity_alignment(self, event: Event, identity_key: str) -> float:
        """
        Baseline identity alignment — how close is this event to the observer's identity.
        All thresholds come from constants.py — no magic numbers in logic.
        """
        if not identity_key:
            return PRISM_ALIGNMENT_ANONYMOUS

        owner = event.source_id or event.temporal_metadata.get("owner_id")

        if owner == identity_key:
            return PRISM_ALIGNMENT_OWNER

        if identity_key in event.raw_data_anchor:
            return PRISM_ALIGNMENT_TOKEN_MATCH

        return PRISM_ALIGNMENT_DEFAULT

    def calculate_personal_weight(
        self,
        event: Event,
        observer: Optional[ObserverContext],
    ) -> tuple[float, str, List[str]]:
        """
        Computes the observer-specific weight and label for an event.

        Returns:
            (personal_multiplier, context_label, insight_components)

        The meaning is relational: the same event has different weight and label
        depending on who is observing and what their context is.

        No hardcoded judgments about what is "good", "bad", "life", or "death".
        Those definitions come from the observer.
        """
        if not observer:
            return 1.0, None, []

        tokens = [t.lower() for t in event.raw_data_anchor]
        multiplier = 1.0
        insight_components = []
        matched_label = None

        # Apply observer's personal token weights
        for token in tokens:
            if token in observer.token_weights:
                w = observer.token_weights[token]
                multiplier *= (1.0 + w) if w > 0 else max(PRISM_PERSONAL_WEIGHT_MIN, 1.0 + w)
                if abs(w) >= PRISM_PERSONAL_WEIGHT_RESONANCE_THRESHOLD:
                    insight_components.append(f"Resonates: {token}")

        # Resolve label from observer's vocabulary
        # First category whose tokens overlap with the event tokens wins
        for label, vocab_tokens in observer.vocabulary.items():
            vocab_set = set(t.lower() for t in vocab_tokens)
            if vocab_set & set(tokens):
                matched_label = label
                insight_components.append(f"Mapped: {label}")
                break

        return multiplier, matched_label, insight_components

    def _default_label(self, alignment: float) -> str:
        """
        Fallback label when observer provides no vocabulary.
        Values come from constants.py — not hardcoded here.
        """
        return PRISM_LABEL_SUBJECTIVE if alignment > PRISM_ALIGNMENT_DEFAULT else PRISM_LABEL_OBJECTIVE

    def _compute_perception_gap(self, candidates: List[Dict]) -> float:
        """
        Measures the perceptual ambiguity in the candidate set.
        0.0 = one clear reading dominates
        1.0 = competing readings are equally valid and contradictory
        """
        if len(candidates) < PRISM_PARADOX_MIN_CANDIDATES:
            return 0.0

        top = candidates[0]
        runner_up = candidates[1]

        s1 = top["score"]
        s2 = runner_up["score"]

        if s1 == 0:
            return 0.0

        score_proximity = 1.0 - abs(s1 - s2) / s1
        score_proximity = max(0.0, min(1.0, score_proximity))

        label_divergence = 0.0 if (
            top["meaning"].context_label == runner_up["meaning"].context_label
        ) else 1.0

        return round(score_proximity * label_divergence, 4)

    def synthesize(
        self,
        query: str,
        identity_key: str,
        resonance_cloud: List[ResonanceResult],
        top_k: int = 3,
        observer: Optional[ObserverContext] = None,
    ) -> Optional[PrismResult]:
        """
        Cognitive synthesis with relational meaning.

        Meaning is not stored in the event. It emerges from the encounter
        between the event and the observer's context.

        The system does not judge what is "good" or "bad", "life" or "death".
        The observer's ObserverContext defines:
        - Which tokens carry personal weight (token_weights)
        - What categories things fall into (vocabulary)
        - Which resonance types matter more (harmonic_weights)

        If no observer context is provided — the system is neutral.
        """
        if not self.indb or not resonance_cloud:
            return None

        candidates = []

        for res in resonance_cloud:
            event = self.indb.get_event(res.event_id)
            if not event:
                continue

            # 1. Global Mass (Fusion Density) — same for all observers
            mass = PRISM_MASS_BASE + math.log(max(1, event.fusion_count))

            # 2. Resonance (from Echo)
            resonance = res.score

            # 3. Harmonic type weight — observer-specific or default 1.0
            harmonic_multiplier = 1.0
            if observer and res.harmonic_type in observer.harmonic_weights:
                harmonic_multiplier = observer.harmonic_weights[res.harmonic_type]

            # 4. Identity Alignment — structural
            alignment = self.calculate_identity_alignment(event, identity_key)

            # 5. Personal Weight + Label — relational, observer-defined
            personal_weight, personal_label, personal_insights = self.calculate_personal_weight(
                event, observer
            )

            # Full formula: S_score = (Mass * Resonance * HarmonicWeight) * Alignment * PersonalWeight
            s_score = (mass * resonance * harmonic_multiplier) * alignment * personal_weight

            # Build insight
            insight_components = list(personal_insights)
            if alignment > PRISM_INSIGHT_DEEPLY_PERSONAL_ALIGNMENT:
                insight_components.append(PRISM_INSIGHT_DEEPLY_PERSONAL)
            if mass > PRISM_MASS_COLLECTIVE_THRESHOLD:
                insight_components.append(PRISM_INSIGHT_COLLECTIVE_TRUTH)
            if res.harmonic_type == "emotional":
                insight_components.append(PRISM_INSIGHT_EMOTIONAL_MATCH)
            elif res.harmonic_type == "cyclic":
                insight_components.append(PRISM_INSIGHT_TIME_ECHO)

            # Label: observer's vocabulary wins; fallback to structural default
            context_label = personal_label or self._default_label(alignment)

            if not insight_components:
                insight_components.append(PRISM_INSIGHT_DIRECT_HIT)

            candidates.append({
                "event": event,
                "score": s_score,
                "meaning": MeaningVector(
                    significance_score=round(s_score, 4),
                    context_label=context_label,
                    insight=" + ".join(insight_components),
                ),
            })

        if not candidates:
            return None

        candidates.sort(key=lambda x: x["score"], reverse=True)

        perception_gap = self._compute_perception_gap(candidates)
        is_paradoxical = (
            len(candidates) >= PRISM_PARADOX_MIN_CANDIDATES
            and perception_gap >= PRISM_PARADOX_SCORE_PROXIMITY_THRESHOLD
        )

        winner = candidates[0]
        winner_event_obj = winner["event"]
        winner_event_response = EventResponse(**winner_event_obj.to_dict())

        alternative_readings = [
            c["meaning"] for c in candidates[1:top_k]
            if c["score"] > 0
        ]

        has_unread_essence = bool(getattr(winner_event_obj, "blind_payload", None))

        return PrismResult(
            event=winner_event_response,
            meaning=winner["meaning"],
            alternative_readings=alternative_readings,
            is_paradoxical=is_paradoxical,
            perception_gap=perception_gap,
            has_unread_essence=has_unread_essence,
        )
