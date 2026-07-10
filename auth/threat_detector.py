"""
Threat Detection Interpreter for INDB
Identifies real risks, dangers, and threats in events
Reality-based, no sugarcoating
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import time

class ThreatLevel:
    """Threat severity levels"""
    CRITICAL = "critical"  # Immediate danger
    HIGH = "high"          # Serious risk
    MEDIUM = "medium"      # Moderate concern
    LOW = "low"            # Minor issue
    NONE = "none"          # No threat

class ThreatCategory:
    """
    Extensible threat category definition
    
    Allows users to define custom threat categories
    """
    def __init__(self, name: str, indicators: Dict[str, float], description: str = ""):
        self.name = name
        self.indicators = indicators  # {indicator: weight}
        self.description = description
    
    def to_dict(self):
        return {
            "name": self.name,
            "indicators": self.indicators,
            "description": self.description
        }

class ThreatDetector:
    """
    Detects threats and risks in events
    
    Philosophy: Truth > Comfort
    Purpose: Identify real dangers so user can take action
    
    Features:
    - Extensible: Add custom threat categories
    - Focusable: Analyze specific categories only
    """
    
    # Default threat categories
    DEFAULT_CATEGORIES = {
        "career": ThreatCategory(
            name="career",
            description="Job security and professional risks",
            indicators={
                "vague_feedback": 0.6,
                "avoided_communication": 0.7,
                "excluded_meetings": 0.8,
                "workload_reduction": 0.7,
                "micromanagement": 0.6,
                "documentation_requests": 0.5,
                "performance_review": 0.4
            }
        ),
        "relationship": ThreatCategory(
            name="relationship",
            description="Relationship health and stability",
            indicators={
                "communication_decline": 0.7,
                "conflict_avoidance": 0.6,
                "emotional_distance": 0.8,
                "criticism_increase": 0.7,
                "intimacy_decline": 0.8,
                "third_party_involvement": 0.9,
                "financial_secrecy": 0.8
            }
        ),
        "health": ThreatCategory(
            name="health",
            description="Physical and mental health risks",
            indicators={
                "sleep_decline": 0.7,
                "energy_crash": 0.6,
                "pain_persistent": 0.8,
                "appetite_change": 0.6,
                "substance_increase": 0.9,
                "isolation": 0.7,
                "suicidal_thoughts": 1.0
            }
        ),
        "financial": ThreatCategory(
            name="financial",
            description="Financial stability and security",
            indicators={
                "debt_accumulation": 0.8,
                "income_decline": 0.9,
                "expense_increase": 0.6,
                "savings_depletion": 0.7,
                "investment_loss": 0.6,
                "job_insecurity": 0.8
            }
        )
    }
    
    def __init__(self, custom_categories: Optional[Dict[str, ThreatCategory]] = None):
        """
        Initialize ThreatDetector
        
        Args:
            custom_categories: Optional custom threat categories to add/override
        """
        self.threat_history = []
        
        # Start with default categories
        self.categories = self.DEFAULT_CATEGORIES.copy()
        
        # Add/override with custom categories
        if custom_categories:
            self.categories.update(custom_categories)
    
    def add_category(self, category: ThreatCategory):
        """
        Add or update a threat category
        
        Args:
            category: ThreatCategory to add
        """
        self.categories[category.name] = category
    
    def remove_category(self, category_name: str):
        """Remove a threat category"""
        if category_name in self.categories:
            del self.categories[category_name]
    
    def get_categories(self) -> List[str]:
        """Get list of available category names"""
        return list(self.categories.keys())
    
    def get_category_info(self, category_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific category"""
        category = self.categories.get(category_name)
        return category.to_dict() if category else None
    
    def detect_threats(
        self,
        event: Dict[str, Any],
        context: Dict[str, Any],
        historical_events: Optional[List[Dict[str, Any]]] = None,
        focus_categories: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Detect threats in an event
        
        Args:
            event: Event to analyze
            context: Current context
            historical_events: Past events for pattern detection
            focus_categories: Optional list of category names to focus on
                            If None, analyzes all categories
                            Example: ["career", "health"] - only check career and health
        
        Returns:
            Threat analysis with level, factors, and recommendations
        """
        tokens = event.get("interpretation", {}).get("tokens", [])
        location = event.get("original_location", "")
        
        # Determine which categories to analyze
        categories_to_check = focus_categories if focus_categories else list(self.categories.keys())
        
        # Validate focus categories
        if focus_categories:
            invalid = [c for c in focus_categories if c not in self.categories]
            if invalid:
                return {
                    "error": f"Invalid categories: {invalid}",
                    "available_categories": self.get_categories()
                }
        
        # Analyze threat indicators
        threats = []
        
        for category_name in categories_to_check:
            category = self.categories[category_name]
            threat = self._analyze_category_threats(category, tokens, location)
            if threat:
                threats.append(threat)
        
        # Pattern-based threats (if not focusing on specific categories)
        if not focus_categories and historical_events:
            pattern_threats = self._analyze_patterns(event, historical_events)
            threats.extend(pattern_threats)
        
        # Calculate overall threat level
        if not threats:
            return {
                "threat_level": ThreatLevel.NONE,
                "threats": [],
                "overall_risk": 0.0,
                "message": "No significant threats detected",
                "categories_checked": categories_to_check
            }
        
        # Sort by severity
        threats.sort(key=lambda x: x["severity"], reverse=True)
        
        highest_severity = threats[0]["severity"]
        threat_level = self._severity_to_level(highest_severity)
        
        return {
            "threat_level": threat_level,
            "threats": threats,
            "overall_risk": highest_severity,
            "primary_threat": threats[0],
            "threat_count": len(threats),
            "requires_action": highest_severity >= 0.6,
            "urgency": self._calculate_urgency(threats),
            "categories_checked": categories_to_check,
            "focus_mode": bool(focus_categories)
        }
    
    def _analyze_career_threats(self, tokens: List[str], location: str) -> Optional[Dict[str, Any]]:
        """Detect career-related threats"""
        threat_score = 0.0
        indicators = []
        
        for token in tokens:
            for threat_indicator, weight in self.CAREER_THREATS.items():
                if threat_indicator.replace("_", " ") in token.lower():
                    threat_score = max(threat_score, weight)
                    indicators.append(threat_indicator)
        
        if threat_score == 0:
            return None
        
        # Context-specific analysis
        if "work" in location.lower() or "office" in location.lower():
            threat_score *= 1.2  # Higher risk at work location
        
        return {
            "category": "career",
            "severity": min(threat_score, 1.0),
            "indicators": indicators,
            "description": self._generate_career_threat_description(indicators, threat_score),
            "recommended_actions": self._get_career_actions(indicators, threat_score)
        }
    
    def _analyze_relationship_threats(self, tokens: List[str]) -> Optional[Dict[str, Any]]:
        """Detect relationship threats"""
        threat_score = 0.0
        indicators = []
        
        for token in tokens:
            for threat_indicator, weight in self.RELATIONSHIP_THREATS.items():
                if threat_indicator.replace("_", " ") in token.lower():
                    threat_score = max(threat_score, weight)
                    indicators.append(threat_indicator)
        
        if threat_score == 0:
            return None
        
        return {
            "category": "relationship",
            "severity": min(threat_score, 1.0),
            "indicators": indicators,
            "description": self._generate_relationship_threat_description(indicators, threat_score),
            "recommended_actions": self._get_relationship_actions(indicators, threat_score)
        }
    
    def _analyze_health_threats(self, tokens: List[str]) -> Optional[Dict[str, Any]]:
        """Detect health threats"""
        threat_score = 0.0
        indicators = []
        
        for token in tokens:
            for threat_indicator, weight in self.HEALTH_THREATS.items():
                if threat_indicator.replace("_", " ") in token.lower():
                    threat_score = max(threat_score, weight)
                    indicators.append(threat_indicator)
        
        if threat_score == 0:
            return None
        
        return {
            "category": "health",
            "severity": min(threat_score, 1.0),
            "indicators": indicators,
            "description": self._generate_health_threat_description(indicators, threat_score),
            "recommended_actions": self._get_health_actions(indicators, threat_score),
            "urgency": "immediate" if threat_score >= 0.9 else "high" if threat_score >= 0.7 else "moderate"
        }
    
    def _analyze_financial_threats(self, tokens: List[str]) -> Optional[Dict[str, Any]]:
        """Detect financial threats"""
        threat_score = 0.0
        indicators = []
        
        for token in tokens:
            for threat_indicator, weight in self.FINANCIAL_THREATS.items():
                if threat_indicator.replace("_", " ") in token.lower():
                    threat_score = max(threat_score, weight)
                    indicators.append(threat_indicator)
        
        if threat_score == 0:
            return None
        
        return {
            "category": "financial",
            "severity": min(threat_score, 1.0),
            "indicators": indicators,
            "description": self._generate_financial_threat_description(indicators, threat_score),
            "recommended_actions": self._get_financial_actions(indicators, threat_score)
        }
    
    def _analyze_patterns(
        self,
        current_event: Dict[str, Any],
        historical_events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Detect threatening patterns"""
        threats = []
        
        # Look for escalating patterns
        current_tokens = set(current_event.get("interpretation", {}).get("tokens", []))
        
        # Find similar events in past
        similar_events = []
        for event in historical_events[-20:]:  # Last 20 events
            event_tokens = set(event.get("interpretation", {}).get("tokens", []))
            similarity = len(current_tokens & event_tokens) / len(current_tokens | event_tokens) if current_tokens | event_tokens else 0
            
            if similarity > 0.5:
                similar_events.append(event)
        
        # If pattern repeats frequently, it's a threat
        if len(similar_events) >= 3:
            threats.append({
                "category": "pattern",
                "severity": min(0.5 + (len(similar_events) * 0.1), 0.9),
                "indicators": ["recurring_pattern"],
                "description": f"Pattern detected: Similar event occurred {len(similar_events)} times recently",
                "recommended_actions": [
                    "Identify root cause of recurring pattern",
                    "Break the cycle - change approach",
                    "Seek external help if pattern persists"
                ],
                "pattern_frequency": len(similar_events),
                "escalation_risk": "high" if len(similar_events) >= 5 else "moderate"
            })
        
        return threats
    
    def _severity_to_level(self, severity: float) -> str:
        """Convert severity score to threat level"""
        if severity >= 0.9:
            return ThreatLevel.CRITICAL
        elif severity >= 0.7:
            return ThreatLevel.HIGH
        elif severity >= 0.5:
            return ThreatLevel.MEDIUM
        elif severity >= 0.3:
            return ThreatLevel.LOW
        else:
            return ThreatLevel.NONE
    
    def _calculate_urgency(self, threats: List[Dict[str, Any]]) -> str:
        """Calculate urgency level"""
        max_severity = max(t["severity"] for t in threats)
        
        if max_severity >= 0.9:
            return "immediate"
        elif max_severity >= 0.7:
            return "high"
        elif max_severity >= 0.5:
            return "moderate"
        else:
            return "low"
    
    def _generate_career_threat_description(self, indicators: List[str], severity: float) -> str:
        """Generate career threat description"""
        if severity >= 0.8:
            return "HIGH RISK: Job security threatened. Multiple warning signs detected."
        elif severity >= 0.6:
            return "MODERATE RISK: Career concerns detected. Monitor situation closely."
        else:
            return "LOW RISK: Minor career concerns. Stay aware."
    
    def _generate_relationship_threat_description(self, indicators: List[str], severity: float) -> str:
        """Generate relationship threat description"""
        if severity >= 0.8:
            return "HIGH RISK: Relationship in danger. Immediate intervention needed."
        elif severity >= 0.6:
            return "MODERATE RISK: Relationship strain detected. Address issues soon."
        else:
            return "LOW RISK: Minor relationship concerns."
    
    def _generate_health_threat_description(self, indicators: List[str], severity: float) -> str:
        """Generate health threat description"""
        if severity >= 0.9:
            return "CRITICAL: Serious health risk. Seek immediate professional help."
        elif severity >= 0.7:
            return "HIGH RISK: Significant health concerns. Medical consultation recommended."
        else:
            return "MODERATE RISK: Health monitoring advised."
    
    def _generate_financial_threat_description(self, indicators: List[str], severity: float) -> str:
        """Generate financial threat description"""
        if severity >= 0.8:
            return "HIGH RISK: Financial crisis developing. Immediate action required."
        elif severity >= 0.6:
            return "MODERATE RISK: Financial concerns. Review budget and expenses."
        else:
            return "LOW RISK: Minor financial monitoring needed."
    
    def _get_career_actions(self, indicators: List[str], severity: float) -> List[str]:
        """Get recommended actions for career threats"""
        actions = []
        
        if severity >= 0.7:
            actions.append("Update resume immediately")
            actions.append("Start job search")
            actions.append("Document all work and achievements")
        
        if "vague_feedback" in indicators:
            actions.append("Request explicit, written feedback")
        
        if "excluded_meetings" in indicators:
            actions.append("Ask directly about exclusion reasons")
        
        actions.append("Network with colleagues and industry contacts")
        
        return actions
    
    def _get_relationship_actions(self, indicators: List[str], severity: float) -> List[str]:
        """Get recommended actions for relationship threats"""
        actions = []
        
        if severity >= 0.8:
            actions.append("Seek couples therapy/counseling")
            actions.append("Have honest conversation about relationship status")
        
        if "communication_decline" in indicators:
            actions.append("Schedule dedicated communication time")
        
        if "emotional_distance" in indicators:
            actions.append("Plan quality time together")
        
        return actions
    
    def _get_health_actions(self, indicators: List[str], severity: float) -> List[str]:
        """Get recommended actions for health threats"""
        actions = []
        
        if severity >= 0.9:
            actions.append("SEEK IMMEDIATE MEDICAL HELP")
        
        if severity >= 0.7:
            actions.append("Schedule doctor appointment this week")
        
        if "sleep_decline" in indicators:
            actions.append("Prioritize sleep hygiene")
        
        if "substance_increase" in indicators:
            actions.append("Consider addiction support resources")
        
        return actions
    
    def _get_financial_actions(self, indicators: List[str], severity: float) -> List[str]:
        """Get recommended actions for financial threats"""
        actions = []
        
        if severity >= 0.8:
            actions.append("Create emergency budget")
            actions.append("Seek financial advisor consultation")
        
        if "debt_accumulation" in indicators:
            actions.append("Stop non-essential spending")
            actions.append("Create debt repayment plan")
        
        if "income_decline" in indicators:
            actions.append("Explore additional income sources")
        
        return actions

# Global threat detector instance
default_threat_detector = ThreatDetector()

def detect_threats(
    event: Dict[str, Any],
    context: Dict[str, Any],
    historical_events: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Convenience function for threat detection
    
    Args:
        event: Event to analyze
        context: Current context
        historical_events: Past events for pattern detection
    
    Returns:
        Threat analysis
    """
    return default_threat_detector.detect_threats(event, context, historical_events)
