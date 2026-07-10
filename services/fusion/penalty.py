"""
Penalty System for INDB Fusion Engine

Transforms naive token matching into intelligent contextual interpretation.
This is the core differentiator between INDB and SQL/Document databases.

Three penalty types:
1. FrequencyPenalty - High-frequency tokens lose weight (TF-IDF inspired)
2. IsolationPenalty - Single-match connections are dropped
3. ContextGapPenalty - Cross-context connections are heavily penalized
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Any, Optional


# Protected prefixes - these tokens are NEVER penalized
PROTECTED_PREFIXES = [
    "category:",
    "era:",
    "coordinates:",
    "osm:",
    "significance:",
    "author:",
    "event:",
]


@dataclass
class PenaltyConfig:
    """Configuration for the Penalty System"""
    
    # Frequency Penalty
    high_freq_threshold: int = 50       # Token appears > N times → penalize
    high_freq_penalty: float = 0.9      # Reduce weight by 90%
    
    # Isolation Penalty
    min_overlap_tokens: int = 2         # Minimum shared tokens to consider
    isolation_drop: bool = True         # DROP if below minimum
    
    # Context Gap Penalty
    context_mismatch_penalty: float = 0.8  # Reduce by 80% on era/category mismatch
    strict_context: bool = True            # Require both era AND category match
    
    # Final threshold
    drop_threshold: float = 0.1         # Drop if final score < this


@dataclass
class PenaltyResult:
    """Result of penalty application"""
    original_score: float
    final_score: float
    decision: str  # "accept", "penalized", "drop"
    penalties_applied: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


class PenaltyEngine:
    """
    Intelligent penalty engine for fusion decisions.
    
    This is the brain that prevents "Jerusalem = Tokyo" type errors.
    """
    
    def __init__(self, config: Optional[PenaltyConfig] = None):
        self.config = config or PenaltyConfig()
        self.corpus_stats: Dict[str, int] = {}
        self.total_events: int = 0
    
    def update_corpus_stats(self, tokens: List[str]):
        """Update corpus statistics with new tokens from an event"""
        self.total_events += 1
        for token in tokens:
            self.corpus_stats[token] = self.corpus_stats.get(token, 0) + 1
    
    def load_corpus_stats(self, stats: Dict[str, int], total: int):
        """Load corpus statistics from persistence"""
        self.corpus_stats = stats
        self.total_events = total
    
    def get_corpus_stats(self) -> Tuple[Dict[str, int], int]:
        """Get corpus statistics for persistence"""
        return self.corpus_stats, self.total_events
    
    def apply(
        self,
        event1_tokens: List[str],
        event2_tokens: List[str],
        raw_similarity: float,
        event1_location: str = "",
        event2_location: str = ""
    ) -> PenaltyResult:
        """
        Apply all penalties to a similarity score.
        
        Args:
            event1_tokens: Tokens from first event
            event2_tokens: Tokens from second event
            raw_similarity: Raw similarity score (0-1)
            event1_location: Location of first event
            event2_location: Location of second event
            
        Returns:
            PenaltyResult with final score and decision
        """
        penalties_applied = []
        details = {}
        multiplier = 1.0
        
        # Calculate shared tokens
        set1 = set(event1_tokens)
        set2 = set(event2_tokens)
        shared_tokens = set1 & set2
        
        details["shared_tokens"] = list(shared_tokens)[:10]  # Limit for display
        details["shared_count"] = len(shared_tokens)
        
        # --- 1. ISOLATION PENALTY ---
        isolation_result = self._apply_isolation_penalty(shared_tokens)
        if isolation_result["drop"]:
            return PenaltyResult(
                original_score=raw_similarity,
                final_score=0.0,
                decision="drop",
                penalties_applied=["isolation"],
                details={"reason": "Too few shared tokens", "count": len(shared_tokens)}
            )
        if isolation_result["penalty"] < 1.0:
            multiplier *= isolation_result["penalty"]
            penalties_applied.append("isolation")
        
        # --- 2. FREQUENCY PENALTY ---
        freq_result = self._apply_frequency_penalty(shared_tokens)
        multiplier *= freq_result["multiplier"]
        if freq_result["penalized_tokens"]:
            penalties_applied.append("frequency")
            details["high_freq_tokens"] = freq_result["penalized_tokens"]
        
        # --- 3. CONTEXT GAP PENALTY ---
        ctx1 = self._extract_context(event1_tokens)
        ctx2 = self._extract_context(event2_tokens)
        context_result = self._apply_context_penalty(ctx1, ctx2)
        
        if context_result["drop"]:
            return PenaltyResult(
                original_score=raw_similarity,
                final_score=0.0,
                decision="drop",
                penalties_applied=["context_gap"],
                details={
                    "reason": "Context mismatch",
                    "ctx1": ctx1,
                    "ctx2": ctx2
                }
            )
        
        if context_result["penalty"] < 1.0:
            multiplier *= context_result["penalty"]
            penalties_applied.append("context_gap")
            details["context_mismatch"] = context_result["mismatches"]
        
        # --- FINAL SCORE ---
        final_score = raw_similarity * multiplier
        
        # Check drop threshold
        if final_score < self.config.drop_threshold:
            return PenaltyResult(
                original_score=raw_similarity,
                final_score=0.0,
                decision="drop",
                penalties_applied=penalties_applied,
                details=details
            )
        
        decision = "penalized" if penalties_applied else "accept"
        
        return PenaltyResult(
            original_score=raw_similarity,
            final_score=round(final_score, 4),
            decision=decision,
            penalties_applied=penalties_applied,
            details=details
        )
    
    def _apply_isolation_penalty(self, shared_tokens: Set[str]) -> Dict[str, Any]:
        """Check isolation penalty based on shared token count"""
        # Filter out protected tokens for isolation check
        unprotected_shared = [
            t for t in shared_tokens 
            if not any(t.startswith(p) for p in PROTECTED_PREFIXES)
        ]
        
        # Protected tokens count as strong connections
        protected_shared = len(shared_tokens) - len(unprotected_shared)
        effective_count = len(unprotected_shared) + (protected_shared * 2)  # Protected worth 2x
        
        if effective_count < self.config.min_overlap_tokens:
            if self.config.isolation_drop:
                return {"drop": True, "penalty": 0.0}
            else:
                return {"drop": False, "penalty": 0.5}
        
        return {"drop": False, "penalty": 1.0}
    
    def _apply_frequency_penalty(self, shared_tokens: Set[str]) -> Dict[str, Any]:
        """Apply TF-IDF inspired frequency penalty"""
        if not shared_tokens or not self.corpus_stats or self.total_events < 20:
            return {"multiplier": 1.0, "penalized_tokens": []}
        
        total_weight = 0.0
        penalized_tokens = []
        
        for token in shared_tokens:
            # Skip protected tokens
            if any(token.startswith(p) for p in PROTECTED_PREFIXES):
                total_weight += 1.0
                continue
            
            freq = self.corpus_stats.get(token, 1)
            
            if freq > self.config.high_freq_threshold:
                # Heavy penalty for very common tokens
                weight = 1.0 - self.config.high_freq_penalty
                penalized_tokens.append(token)
            else:
                # IDF-inspired weight
                if self.total_events > 0:
                    idf = math.log(self.total_events / (1 + freq))
                    weight = min(1.0, max(0.1, idf / 5.0))  # Normalize to 0.1-1.0
                else:
                    weight = 1.0
            
            total_weight += weight
        
        # Normalize
        if shared_tokens:
            avg_weight = total_weight / len(shared_tokens)
        else:
            avg_weight = 1.0
        
        return {
            "multiplier": avg_weight,
            "penalized_tokens": penalized_tokens
        }
    
    def _extract_context(self, tokens: List[str]) -> Dict[str, str]:
        """Extract context markers from tokens"""
        context = {
            "category": "unknown",
            "era": "unknown",
            "significance": "unknown"
        }
        
        for token in tokens:
            if token.startswith("category:"):
                context["category"] = token.split(":", 1)[1]
            elif token.startswith("era:"):
                context["era"] = token.split(":", 1)[1]
            elif token.startswith("significance:"):
                context["significance"] = token.split(":", 1)[1]
        
        return context
    
    def _apply_context_penalty(
        self, 
        ctx1: Dict[str, str], 
        ctx2: Dict[str, str]
    ) -> Dict[str, Any]:
        """Apply context gap penalty for cross-context connections"""
        mismatches = []
        
        # Check category mismatch
        category_match = (
            ctx1["category"] == ctx2["category"] or
            ctx1["category"] == "unknown" or
            ctx2["category"] == "unknown"
        )
        if not category_match:
            mismatches.append(f"category:{ctx1['category']}≠{ctx2['category']}")
        
        # Check era mismatch
        era_match = (
            ctx1["era"] == ctx2["era"] or
            ctx1["era"] == "unknown" or
            ctx2["era"] == "unknown"
        )
        if not era_match:
            mismatches.append(f"era:{ctx1['era']}≠{ctx2['era']}")
        
        # Strict mode: both must mismatch for DROP
        if self.config.strict_context:
            if not category_match and not era_match:
                return {"drop": True, "penalty": 0.0, "mismatches": mismatches}
            elif mismatches:
                return {"drop": False, "penalty": 1.0 - self.config.context_mismatch_penalty, "mismatches": mismatches}
        else:
            # Lenient mode: any mismatch applies penalty
            if mismatches:
                penalty = (1.0 - self.config.context_mismatch_penalty) ** len(mismatches)
                return {"drop": False, "penalty": penalty, "mismatches": mismatches}
        
        return {"drop": False, "penalty": 1.0, "mismatches": []}
    
    def explain_decision(self, result: PenaltyResult) -> str:
        """Generate human-readable explanation of penalty decision"""
        lines = [
            f"Original Score: {result.original_score:.3f}",
            f"Final Score: {result.final_score:.3f}",
            f"Decision: {result.decision.upper()}"
        ]
        
        if result.penalties_applied:
            lines.append(f"Penalties: {', '.join(result.penalties_applied)}")
        
        if "reason" in result.details:
            lines.append(f"Reason: {result.details['reason']}")
        
        if "high_freq_tokens" in result.details:
            lines.append(f"High-freq tokens: {result.details['high_freq_tokens']}")
        
        if "context_mismatch" in result.details:
            lines.append(f"Context: {result.details['context_mismatch']}")
        
        return "\n".join(lines)
