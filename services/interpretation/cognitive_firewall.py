"""
Cognitive Firewall for INDB

A context-aware filter system that protects the "Mind" (Database) from 
information that is harmful, irrelevant, or dangerous given the current State.

supports:
- Educational/Emotional filtering (Prevent panic loops)
- Operational filtering (Prevent debug logs in production)
- Security filtering (Redact sensitive tokens in public contexts)
"""

from typing import List, Dict, Any, Optional, Union, Literal
from dataclasses import dataclass, field
from enum import Enum
import re
import json

class FirewallAction(Enum):
    ALLOW = "allow"
    BLOCK = "block"
    REDACT = "redact"
    WARN = "warn"

@dataclass
class CognitiveRule:
    """
    A single rule for the Cognitive Firewall.
    
    Attributes:
        name: Human-readable name
        condition: A dictionary of key-value pairs to match. 
                   Keys can be 'context.x', 'event.x'.
                   Values can be exact strings or regex (if prefixed with 'regex:')
        action: What to do if condition matches
        priority: Higher priority rules are evaluated first
        redaction_fields: If action is REDACT, which fields to mask
    """
    name: str
    condition: Dict[str, Any]
    action: FirewallAction
    priority: int = 10
    redaction_fields: List[str] = field(default_factory=list)
    custom_message: Optional[str] = None

    def matches(self, event: Any, context: Dict[str, Any]) -> bool:
        """Check if rule matches the given event and context."""
        for key, expected_value in self.condition.items():
            # Resolve value from event or context
            actual_value = None
            if key.startswith("context."):
                part = key.split("context.", 1)[1]
                actual_value = context.get(part)
            elif key.startswith("event."):
                part = key.split("event.", 1)[1]
                # handle event objects or dicts
                if isinstance(event, dict):
                    actual_value = event.get(part)
                else:
                    actual_value = getattr(event, part, None)
            
            # Simple attribute check (can be extended to comparison ops later)
            if actual_value is None:
                return False
                
            # String matching
            str_actual = str(actual_value)
            str_expected = str(expected_value)
            
            if str_expected.startswith("regex:"):
                pattern = str_expected[6:]
                if not re.search(pattern, str_actual, re.IGNORECASE):
                    return False
            elif str_expected == "*":
                pass # universal match if key exists
            else:
                if str_actual.lower() != str_expected.lower():
                    return False
                    
        return True

class CognitiveFirewall:
    """
    The Gatekeeper of Information.
    """
    
    def __init__(self, rules: List[CognitiveRule] = None):
        self.rules = sorted(rules or [], key=lambda x: x.priority, reverse=True)
        
        # Default implicit hygiene rules if empty
        if not rules:
            self._load_defaults()

    def _load_defaults(self):
        """Load standard hygiene rules."""
        self.rules = [
            # Block PANIC signals when already in FEAR state (Prevent feedback loops)
            CognitiveRule(
                name="Prevent Panic Loop",
                condition={
                    "context.mood": "Fear",
                    "event.derived_emotion": "Panic"
                },
                action=FirewallAction.BLOCK,
                priority=100,
                custom_message="Panic signal blocked to prevent spiraling."
            ),
            # Redact AUTH tokens in PUBLIC contexts
            CognitiveRule(
                name="Security Masking",
                condition={
                    "context.security_level": "Public",
                   # Matches broad set of secret-like tokens in raw data
                   # Note: This is a simplification; real matching matches against tokens list
                },
                action=FirewallAction.REDACT,
                priority=90,
                redaction_fields=["narrative", "tokens"]
            ),
            # Operational: Block DEBUG in PRODUCTION
            CognitiveRule(
                name="Silence Debug Noise",
                condition={
                    "context.status": "Production",
                    "event.tag": "DEBUG"
                },
                action=FirewallAction.BLOCK,
                priority=50
            ) 
        ]
        # Sort again
        self.rules.sort(key=lambda x: x.priority, reverse=True)

    def add_rule(self, rule: CognitiveRule):
        self.rules.append(rule)
        self.rules.sort(key=lambda x: x.priority, reverse=True)

    def inspect(self, event: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inspect an event against all rules.
        
        Returns:
            Dict containing decision metadata.
        """
        decision = {
            "allowed": True,
            "modified": False,
            "action": "ALLOW",
            "rule_name": None,
            "reason": None,
            "event": event # Return the (potentially modified) event
        }
        
        for rule in self.rules:
            if rule.matches(event, context):
                decision["rule_name"] = rule.name
                decision["reason"] = rule.custom_message or f"Matched rule: {rule.name}"
                
                if rule.action == FirewallAction.BLOCK:
                    decision["allowed"] = False
                    decision["action"] = "BLOCK"
                    return decision
                
                elif rule.action == FirewallAction.REDACT:
                    # Perform Redaction
                    decision["modified"] = True
                    decision["action"] = "REDACT"
                    decision["event"] = self._redact(event, rule.redaction_fields)
                    # We continue checking other rules? Usually redact is final modification, 
                    # but higher priority BLOCK could still apply? 
                    # For now, we take the highest priority match that modifies/blocks and return.
                    return decision
                    
                elif rule.action == FirewallAction.WARN:
                    decision["action"] = "WARN"
                    decision["warning"] = rule.custom_message
                    # Warn doesn't stop processing, but we return here for simplicity in v1
                    return decision
                    
        return decision

    def _redact(self, event: Any, fields: List[str]) -> Any:
        # Create a shallow copy / dict representation to modify
        if hasattr(event, "to_dict"):
            e_dict = event.to_dict()
        else:
            e_dict = dict(event)
            
        for field_name in fields:
            if field_name == "tokens":
                e_dict["raw_data_anchor"] = ["██████"]
            elif field_name in e_dict:
                e_dict[field_name] = "[REDACTED]"
            elif field_name == "narrative" and "interpretation" in e_dict:
                 e_dict["interpretation"]["narrative"] = "[REDACTED BY FIREWALL]"
                 
        return e_dict
        
    def export_rules(self) -> List[Dict[str, Any]]:
        """Export rules to JSON-serializable list."""
        return [
            {
                "name": r.name,
                "condition": r.condition,
                "action": r.action.value,
                "priority": r.priority,
                "redaction_fields": r.redaction_fields,
                "custom_message": r.custom_message
            }
            for r in self.rules
        ]
        
    @classmethod
    def from_dict_list(cls, rule_list: List[Dict[str, Any]]) -> 'CognitiveFirewall':
        """Load firewall from list of dicts."""
        fw = cls(rules=[])
        # Clear defaults
        fw.rules = []
        for r in rule_list:
            fw.add_rule(CognitiveRule(
                name=r["name"],
                condition=r["condition"],
                action=FirewallAction(r["action"]),
                priority=r.get("priority", 10),
                redaction_fields=r.get("redaction_fields", []),
                custom_message=r.get("custom_message")
            ))
        return fw
