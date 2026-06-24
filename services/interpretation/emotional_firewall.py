"""
Emotional Firewall for INDB
Filters or redacts events based on emotional safety criteria
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from enum import Enum

class FirewallMode(Enum):
    """Firewall operation modes"""
    BLOCK = "block"          # Completely remove events
    REDACT = "redact"        # Show event but hide details
    WARNING = "warning"      # Show with warning flag
    THERAPY = "therapy"      # Bypass firewall (for therapeutic work)

class EmotionalFirewall:
    """
    Protects users from re-traumatization by filtering harmful emotional content.
    
    Inspired by cognitive behavioral therapy and trauma-informed care principles.
    """
    
    # Default banned emotions (can be customized per user)
    DEFAULT_BANNED_EMOTIONS = {
        "Guilt",
        "Shame", 
        "Trauma",
        "Panic",
        "Despair",
        "Self-Hatred"
    }
    
    # Emotions that trigger warnings but aren't blocked
    WARNING_EMOTIONS = {
        "Fear",
        "Anxiety",
        "Sadness",
        "Anger"
    }
    
    def __init__(
        self,
        mode: FirewallMode = FirewallMode.BLOCK,
        banned_emotions: Optional[Set[str]] = None,
        custom_rules: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Emotional Firewall
        
        Args:
            mode: How to handle banned emotions
            banned_emotions: Custom set of emotions to filter
            custom_rules: Additional filtering rules
        """
        self.mode = mode
        self.banned_emotions = banned_emotions or self.DEFAULT_BANNED_EMOTIONS.copy()
        self.custom_rules = custom_rules or {}
    
    def check(self, evt_dict: Dict[str, Any]) -> Tuple[bool, str, str]:
        """
        Check a single event dict. Used by kernel.interpret.
        Returns (allowed, action, reason).
        """
        emotion = evt_dict.get("derived_emotion", "Neutral")
        if emotion in self.banned_emotions:
            if self.mode == FirewallMode.BLOCK:
                return False, "block", f"Emotion '{emotion}' blocked by firewall"
            if self.mode == FirewallMode.REDACT:
                return True, "redact", f"Emotion '{emotion}' redacted"
            if self.mode == FirewallMode.WARNING:
                return True, "warn", f"Emotion '{emotion}' flagged"
        return True, "allow", ""

    def filter_events(
        self,
        events: List[Dict[str, Any]],
        bypass: bool = False
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Filter events through emotional firewall
        
        Args:
            events: List of interpreted events
            bypass: If True, bypass firewall (therapy mode)
        
        Returns:
            Tuple of (filtered_events, firewall_report)
        """
        if bypass or self.mode == FirewallMode.THERAPY:
            return events, {
                "firewall_active": False,
                "mode": "therapy",
                "blocked_count": 0,
                "warning_count": 0
            }
        
        filtered_events = []
        blocked_count = 0
        warning_count = 0
        blocked_emotions = {}
        
        for event in events:
            emotion = event.get("derived_emotion", "Neutral")
            
            # Check if emotion is banned
            if emotion in self.banned_emotions:
                blocked_count += 1
                blocked_emotions[emotion] = blocked_emotions.get(emotion, 0) + 1
                
                if self.mode == FirewallMode.BLOCK:
                    # Skip this event entirely
                    continue
                
                elif self.mode == FirewallMode.REDACT:
                    # Redact sensitive details
                    event = self._redact_event(event)
                    event["firewall_redacted"] = True
                    filtered_events.append(event)
                
                elif self.mode == FirewallMode.WARNING:
                    # Add warning flag
                    event["firewall_warning"] = True
                    event["warning_reason"] = f"Contains potentially triggering emotion: {emotion}"
                    filtered_events.append(event)
            
            # Check for warning emotions
            elif emotion in self.WARNING_EMOTIONS:
                warning_count += 1
                event["firewall_caution"] = True
                filtered_events.append(event)
            
            else:
                # Safe emotion - pass through
                filtered_events.append(event)
        
        firewall_report = {
            "firewall_active": True,
            "mode": self.mode.value,
            "blocked_count": blocked_count,
            "warning_count": warning_count,
            "blocked_emotions": blocked_emotions,
            "banned_emotions_list": list(self.banned_emotions)
        }
        
        return filtered_events, firewall_report
    
    def _redact_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact sensitive details from event
        
        Keeps structure but removes potentially triggering content
        """
        redacted = event.copy()
        
        # Redact narrative
        if "interpretation" in redacted:
            redacted["interpretation"] = {
                "narrative": "[REDACTED FOR EMOTIONAL SAFETY]",
                "emotional_weight": 0.0,
                "tokens": ["[redacted]"]
            }
        
        # Keep metadata for context
        redacted["redaction_reason"] = f"Emotion '{event.get('derived_emotion')}' is filtered by firewall"
        
        return redacted
    
    def add_banned_emotion(self, emotion: str):
        """Add emotion to banned list"""
        self.banned_emotions.add(emotion)
    
    def remove_banned_emotion(self, emotion: str):
        """Remove emotion from banned list"""
        self.banned_emotions.discard(emotion)
    
    def set_mode(self, mode: FirewallMode):
        """Change firewall mode"""
        self.mode = mode
    
    def get_config(self) -> Dict[str, Any]:
        """Get current firewall configuration"""
        return {
            "mode": self.mode.value,
            "banned_emotions": list(self.banned_emotions),
            "warning_emotions": list(self.WARNING_EMOTIONS)
        }
    
    @classmethod
    def create_therapy_mode(cls) -> 'EmotionalFirewall':
        """
        Create firewall in therapy mode (bypass all filtering)
        
        Use when working with therapist to process traumatic memories
        """
        return cls(mode=FirewallMode.THERAPY)
    
    @classmethod
    def create_safe_mode(cls) -> 'EmotionalFirewall':
        """
        Create firewall in maximum safety mode
        
        Blocks all potentially harmful emotions
        """
        return cls(
            mode=FirewallMode.BLOCK,
            banned_emotions=cls.DEFAULT_BANNED_EMOTIONS | cls.WARNING_EMOTIONS
        )

# Global firewall instance (can be configured per user in future)
default_firewall = EmotionalFirewall(mode=FirewallMode.BLOCK)

def apply_firewall(
    events: List[Dict[str, Any]],
    firewall: Optional[EmotionalFirewall] = None,
    bypass: bool = False
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Convenience function to apply emotional firewall
    
    Args:
        events: Events to filter
        firewall: Custom firewall instance (uses default if None)
        bypass: Bypass firewall (therapy mode)
    
    Returns:
        Tuple of (filtered_events, firewall_report)
    """
    fw = firewall or default_firewall
    return fw.filter_events(events, bypass=bypass)
