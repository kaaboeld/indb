"""
Source Entity for INDB

Represents the origin of an Event. 
Crucial for the "Cognitive Nervous System" paradigm: allows the kernel to weigh
information based on the reliability and type of its origin.
"""

from enum import Enum, auto
from typing import Dict, Any, Optional
import time
import uuid

class SourceType(str, Enum):
    """
    Hierarchy of Verification (Epistemological Class).
    """
    AXIOM = "axiom"        # Hardware/Kernel truth (The "Eyes"). Highest Authority.
    SENSOR = "sensor"      # Calibrated hardware. High Trust.
    SYSTEM = "system"      # Internal software components. High Trust.
    AGENT = "agent"        # AI Agents/Parsers. Variable Trust (needs logic verification).
    HUMAN = "human"        # Human Operators. Subjective.
    CROWD = "crowd"        # Social/Public input. Low Trust (needs consensus).
    UNKNOWN = "unknown"    # Unverified. Zero Trust.

class Source:
    """
    The Passport of an Agent/Sensor in the system.
    """
    def __init__(
        self,
        name: str,
        type: SourceType,
        id: Optional[str] = None,
        reputation: float = 0.5,
        public_key: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None
    ):
        self.id = id if id else str(uuid.uuid4())
        self.name = name
        self.type = type
        self.reputation = self._validate_reputation(reputation)
        self.public_key = public_key
        self.meta = meta or {}
        self.created_at = time.time()
        
    def _validate_reputation(self, rep: float) -> float:
        """Clamp reputation between 0.0 and 1.0"""
        if rep < 0.0: return 0.0
        if rep > 1.0: return 1.0
        return rep

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "reputation": self.reputation,
            "public_key": self.public_key,
            "meta": self.meta,
            "created_at": self.created_at
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Source":
        return Source(
            id=d.get("id"),
            name=d.get("name", "Unknown Source"),
            type=SourceType(d.get("type", "unknown")),
            reputation=d.get("reputation", 0.5),
            public_key=d.get("public_key"),
            meta=d.get("meta")
        )

    def __repr__(self):
        return f"<Source {self.name} ({self.type.value}) Rep:{self.reputation:.2f}>"
