"""
Fuzzy Query Expansion for INDB
Enables human-like, indirect queries with ambiguity and inference
"""

from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
import re

class FuzzyTemporalExpander:
    """
    Expands fuzzy temporal queries with ambiguity
    
    Examples:
        "around summer" → May-September (±1 month)
        "roughly Q3" → Q2 end + Q3 + Q4 start
        "sometime in June" → June ± 2 weeks
    """
    
    # Fuzzy boundaries (in months)
    FUZZY_MARGIN = {
        "around": 1,      # ±1 month
        "roughly": 1,     # ±1 month
        "about": 1,       # ±1 month
        "sometime": 0.5,  # ±2 weeks
        "maybe": 1.5,     # ±6 weeks
    }
    
    def expand_temporal_query(self, query: str) -> Dict[str, Any]:
        """
        Expand fuzzy temporal query
        
        Args:
            query: Fuzzy temporal query (e.g., "around summer")
        
        Returns:
            Expanded temporal criteria with fuzzy boundaries
        """
        query_lower = query.lower()
        
        # Detect fuzzy modifier
        fuzzy_modifier = None
        for modifier in self.FUZZY_MARGIN.keys():
            if modifier in query_lower:
                fuzzy_modifier = modifier
                break
        
        if not fuzzy_modifier:
            # No fuzzy modifier, return exact match
            return self._parse_exact_temporal(query)
        
        # Remove fuzzy modifier to get base temporal
        base_query = query_lower.replace(fuzzy_modifier, "").strip()
        
        # Parse base temporal
        base_criteria = self._parse_exact_temporal(base_query)
        
        # Expand with fuzzy margin
        margin = self.FUZZY_MARGIN[fuzzy_modifier]
        expanded = self._apply_fuzzy_margin(base_criteria, margin)
        
        expanded["fuzzy"] = True
        expanded["fuzzy_modifier"] = fuzzy_modifier
        expanded["fuzzy_margin_months"] = margin
        
        return expanded
    
    def _parse_exact_temporal(self, query: str) -> Dict[str, Any]:
        """Parse exact temporal query (reuse existing logic)"""
        from services.temporal.parser import parse_temporal_query
        return parse_temporal_query(query)
    
    def _apply_fuzzy_margin(self, criteria: Dict[str, Any], margin_months: float) -> Dict[str, Any]:
        """
        Apply fuzzy margin to temporal criteria
        
        Args:
            criteria: Base temporal criteria
            margin_months: Margin in months
        
        Returns:
            Expanded criteria with fuzzy boundaries
        """
        expanded = criteria.copy()
        
        # Expand months
        if "months" in criteria:
            base_months = set(criteria["months"])
            expanded_months = base_months.copy()
            
            for month in base_months:
                # Add previous months
                prev_count = int(margin_months)
                for i in range(1, prev_count + 1):
                    prev_month = month - i
                    if prev_month < 1:
                        prev_month += 12
                    expanded_months.add(prev_month)
                
                # Add next months
                next_count = int(margin_months)
                for i in range(1, next_count + 1):
                    next_month = month + i
                    if next_month > 12:
                        next_month -= 12
                    expanded_months.add(next_month)
            
            expanded["months"] = sorted(list(expanded_months))
            expanded["original_months"] = sorted(list(base_months))
        
        # Expand quarters
        if "quarters" in criteria:
            base_quarters = set(criteria["quarters"])
            expanded_quarters = base_quarters.copy()
            
            # If margin >= 1 month, include adjacent quarters
            if margin_months >= 1:
                for quarter in base_quarters:
                    # Add previous quarter
                    prev_q = quarter - 1 if quarter > 1 else 4
                    expanded_quarters.add(prev_q)
                    # Add next quarter
                    next_q = quarter + 1 if quarter < 4 else 1
                    expanded_quarters.add(next_q)
            
            expanded["quarters"] = sorted(list(expanded_quarters))
            expanded["original_quarters"] = sorted(list(base_quarters))
        
        return expanded


class ImplicitContextInferencer:
    """
    Infers implicit context from explicit parameters
    
    Examples:
        location="Work" → mood="Neutral", context="professional"
        time="Monday morning" → expected_emotion="Anxiety"
    """
    
    # Location-based inference rules
    LOCATION_INFERENCE = {
        "work": {"mood": "Neutral", "context": "professional", "formality": "high"},
        "office": {"mood": "Neutral", "context": "professional", "formality": "high"},
        "home": {"mood": "Neutral", "context": "personal", "formality": "low"},
        "gym": {"mood": "High_Value", "context": "health", "energy": "high"},
        "hospital": {"mood": "Fear", "context": "health", "stress": "high"},
        "bar": {"mood": "Neutral", "context": "social", "formality": "low"},
        "restaurant": {"mood": "High_Value", "context": "social", "formality": "medium"},
    }
    
    # Temporal pattern inference
    TEMPORAL_PATTERNS = {
        "monday_morning": {"expected_emotion": "Anxiety", "confidence": 0.7, "reason": "Common pattern: Monday morning stress"},
        "friday_evening": {"expected_emotion": "Joy", "confidence": 0.8, "reason": "Weekend anticipation"},
        "sunday_evening": {"expected_emotion": "Sadness", "confidence": 0.6, "reason": "Weekend ending"},
    }
    
    def infer_context(self, explicit_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Infer implicit context from explicit parameters
        
        Args:
            explicit_context: Explicitly provided context
        
        Returns:
            Enhanced context with inferred parameters
        """
        inferred = explicit_context.copy()
        inferred["inferred"] = {}
        
        # Infer from location
        if "location" in explicit_context:
            location = explicit_context["location"].lower()
            for key, inference in self.LOCATION_INFERENCE.items():
                if key in location:
                    for param, value in inference.items():
                        if param not in inferred:
                            inferred[param] = value
                            inferred["inferred"][param] = {
                                "value": value,
                                "source": f"location={location}",
                                "confidence": 0.8
                            }
        
        # Infer from temporal patterns
        if "temporal_query" in explicit_context:
            temporal = explicit_context["temporal_query"].lower().replace(" ", "_")
            if temporal in self.TEMPORAL_PATTERNS:
                pattern = self.TEMPORAL_PATTERNS[temporal]
                inferred["expected_emotion"] = pattern["expected_emotion"]
                inferred["inferred"]["expected_emotion"] = pattern
        
        return inferred


class SemanticTokenExpander:
    """
    Expands tokens with semantic synonyms
    
    Examples:
        ["success"] → ["success", "achievement", "victory", "win"]
        ["fear"] → ["fear", "anxiety", "worry", "dread"]
    """
    
    # Semantic synonym groups
    SYNONYMS = {
        "success": ["success", "achievement", "victory", "win", "triumph", "breakthrough"],
        "failure": ["failure", "defeat", "loss", "setback", "disappointment"],
        "fear": ["fear", "anxiety", "worry", "dread", "panic", "terror"],
        "joy": ["joy", "happiness", "delight", "pleasure", "bliss", "euphoria"],
        "sadness": ["sadness", "sorrow", "grief", "melancholy", "depression"],
        "anger": ["anger", "rage", "fury", "irritation", "frustration"],
        "love": ["love", "affection", "fondness", "adoration", "passion"],
        "work": ["work", "job", "employment", "career", "profession", "occupation"],
        "home": ["home", "house", "residence", "dwelling", "apartment"],
        "friend": ["friend", "buddy", "pal", "companion", "mate"],
    }
    
    def expand_tokens(self, tokens: List[str], expansion_level: str = "moderate") -> Dict[str, Any]:
        """
        Expand tokens with semantic synonyms
        
        Args:
            tokens: Original tokens
            expansion_level: "minimal", "moderate", "aggressive"
        
        Returns:
            Expanded token set with metadata
        """
        expanded_tokens = set(tokens)
        expansion_map = {}
        
        expansion_limits = {
            "minimal": 2,      # Add 2 synonyms per token
            "moderate": 4,     # Add 4 synonyms per token
            "aggressive": 10   # Add all synonyms
        }
        
        limit = expansion_limits.get(expansion_level, 4)
        
        for token in tokens:
            token_lower = token.lower()
            
            # Find synonym group
            for key, synonyms in self.SYNONYMS.items():
                if token_lower == key or token_lower in synonyms:
                    # Add synonyms (limited by expansion level)
                    added = synonyms[:limit]
                    expanded_tokens.update(added)
                    expansion_map[token] = {
                        "original": token,
                        "synonyms_added": added,
                        "expansion_reason": f"Semantic group: {key}"
                    }
                    break
        
        return {
            "original_tokens": tokens,
            "expanded_tokens": sorted(list(expanded_tokens)),
            "expansion_count": len(expanded_tokens) - len(tokens),
            "expansion_map": expansion_map,
            "expansion_level": expansion_level
        }


class ProbabilisticInterpreter:
    """
    Provides probabilistic interpretations for ambiguous events
    
    Examples:
        ["conversation", "ambiguous"] → [
            {"emotion": "Positive", "probability": 0.4},
            {"emotion": "Neutral", "probability": 0.3},
            {"emotion": "Negative", "probability": 0.3}
        ]
    """
    
    # Ambiguity indicators
    AMBIGUOUS_TOKENS = {
        "conversation", "meeting", "discussion", "talk", "chat",
        "ambiguous", "unclear", "mixed", "complicated", "confusing"
    }
    
    def is_ambiguous(self, tokens: List[str]) -> bool:
        """Check if event is ambiguous"""
        token_set = set(t.lower() for t in tokens)
        return bool(token_set & self.AMBIGUOUS_TOKENS)
    
    def generate_probabilistic_interpretation(
        self,
        event: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple probabilistic interpretations
        
        Args:
            event: Event to interpret
            context: Query context
        
        Returns:
            List of possible interpretations with probabilities
        """
        tokens = event.get("interpretation", {}).get("tokens", [])
        
        if not self.is_ambiguous(tokens):
            # Not ambiguous, return single interpretation
            return [{
                "emotion": event.get("derived_emotion", "Neutral"),
                "probability": 1.0,
                "confidence": "high",
                "reason": "Unambiguous event"
            }]
        
        # Generate multiple interpretations
        interpretations = [
            {
                "emotion": "Positive",
                "probability": 0.35,
                "confidence": "low",
                "reason": "Could be positive outcome",
                "indicators": ["conversation", "resolution"]
            },
            {
                "emotion": "Neutral",
                "probability": 0.35,
                "confidence": "medium",
                "reason": "Most likely neutral",
                "indicators": ["discussion", "meeting"]
            },
            {
                "emotion": "Negative",
                "probability": 0.30,
                "confidence": "low",
                "reason": "Could be conflict",
                "indicators": ["ambiguous", "unclear"]
            }
        ]
        
        # Adjust based on context mood
        mood = context.get("mood", "Neutral")
        if mood == "Fear":
            # Bias towards negative
            for interp in interpretations:
                if interp["emotion"] == "Negative":
                    interp["probability"] += 0.2
                else:
                    interp["probability"] -= 0.1
        elif mood == "High_Value":
            # Bias towards positive
            for interp in interpretations:
                if interp["emotion"] == "Positive":
                    interp["probability"] += 0.2
                else:
                    interp["probability"] -= 0.1
        
        # Normalize probabilities
        total = sum(i["probability"] for i in interpretations)
        for interp in interpretations:
            interp["probability"] = round(interp["probability"] / total, 2)
        
        # Sort by probability
        interpretations.sort(key=lambda x: x["probability"], reverse=True)
        
        return interpretations


# Convenience functions
def expand_fuzzy_temporal(query: str) -> Dict[str, Any]:
    """Expand fuzzy temporal query"""
    expander = FuzzyTemporalExpander()
    return expander.expand_temporal_query(query)

def infer_implicit_context(context: Dict[str, Any]) -> Dict[str, Any]:
    """Infer implicit context"""
    inferencer = ImplicitContextInferencer()
    return inferencer.infer_context(context)

def expand_semantic_tokens(tokens: List[str], level: str = "moderate") -> Dict[str, Any]:
    """Expand tokens semantically"""
    expander = SemanticTokenExpander()
    return expander.expand_tokens(tokens, level)

def generate_probabilistic_interpretations(
    event: Dict[str, Any],
    context: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Generate probabilistic interpretations"""
    interpreter = ProbabilisticInterpreter()
    return interpreter.generate_probabilistic_interpretation(event, context)
