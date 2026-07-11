"""
Paradox (type) — pre-observation superposition.

Separate from Event. raw_data_anchor stays empty until collapse.
Not an event_kind flag.
"""

from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

GenerationMode = Literal["resonance_weighted", "pool", "fusion"]
CollapseMode = Literal["sample_once", "sample_on_read"]
ParadoxState = Literal["superposed", "collapsed"]


@dataclass
class ParadoxGeneration:
    mode: GenerationMode = "resonance_weighted"
    collapse: CollapseMode = "sample_once"

    def to_dict(self) -> Dict[str, Any]:
        return {"mode": self.mode, "collapse": self.collapse}

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "ParadoxGeneration":
        data = data or {}
        mode = data.get("mode", "resonance_weighted")
        collapse = data.get("collapse", "sample_once")
        if mode not in ("resonance_weighted", "pool", "fusion"):
            raise ValueError(f"Invalid paradox generation mode: {mode}")
        if collapse not in ("sample_once", "sample_on_read"):
            raise ValueError(f"Invalid paradox collapse mode: {collapse}")
        return cls(mode=mode, collapse=collapse)


@dataclass
class Paradox:
    location: str
    paradox_context: Dict[str, Any] = field(default_factory=dict)
    paradox_generation: ParadoxGeneration = field(default_factory=ParadoxGeneration)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    state: ParadoxState = "superposed"
    raw_data_anchor: List[str] = field(default_factory=list)
    collapsed_anchor: Optional[List[str]] = None
    event_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "state": self.state,
            "location": self.location,
            "raw_data_anchor": self.raw_data_anchor,
            "paradox_context": self.paradox_context,
            "paradox_generation": self.paradox_generation.to_dict(),
            "collapsed_anchor": self.collapsed_anchor,
            "collapsed": self.state == "collapsed",
            "event_id": self.event_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Paradox":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            timestamp=data.get("timestamp", time.time()),
            state=data.get("state", "superposed"),
            location=data["location"],
            raw_data_anchor=list(data.get("raw_data_anchor") or []),
            paradox_context=dict(data.get("paradox_context") or {}),
            paradox_generation=ParadoxGeneration.from_dict(data.get("paradox_generation")),
            collapsed_anchor=data.get("collapsed_anchor"),
            event_id=data.get("event_id"),
        )


class ParadoxEngine:
    """Create and collapse paradox entities."""

    def __init__(self, indb: Any):
        self.indb = indb

    def create(
        self,
        location: str,
        paradox_context: Optional[Dict[str, Any]] = None,
        paradox_generation: Optional[Dict[str, Any]] = None,
    ) -> Paradox:
        if not location or not str(location).strip():
            raise ValueError("location is required")
        generation = ParadoxGeneration.from_dict(paradox_generation)
        paradox = Paradox(
            location=location.strip(),
            paradox_context=dict(paradox_context or {}),
            paradox_generation=generation,
        )
        self.indb.store_paradox(paradox)
        return paradox

    async def collapse(self, paradox_id: str) -> Paradox:
        paradox = self.indb.get_paradox(paradox_id)
        if not paradox:
            raise ValueError("Paradox not found")

        collapse_mode = paradox.paradox_generation.collapse

        if collapse_mode == "sample_once" and paradox.state == "collapsed":
            return paradox

        anchor = self._sample_anchor(paradox)
        paradox.collapsed_anchor = anchor

        if collapse_mode == "sample_once":
            paradox.state = "collapsed"
            paradox.raw_data_anchor = anchor
            if not paradox.event_id:
                from core.kernel import AuthContext

                event_dict = await self.indb.create_event(
                    {
                        "raw_data_anchor": anchor,
                        "location": paradox.location,
                    },
                    AuthContext(user_id="paradox_collapse", auth_method="system"),
                )
                paradox.event_id = event_dict["id"]
            self.indb.store_paradox(paradox)
            return paradox

        # sample_on_read — ephemeral, stays superposed
        paradox.state = "superposed"
        self.indb.store_paradox(paradox)
        return paradox

    def _sample_anchor(self, paradox: Paradox) -> List[str]:
        mode = paradox.paradox_generation.mode
        ctx = paradox.paradox_context
        location = paradox.location

        if mode == "pool":
            pool = list(ctx.get("token_pool") or [])
            if not pool:
                raise ValueError("pool mode requires paradox_context.token_pool")
            k = min(random.randint(1, 3), len(pool))
            return random.sample(pool, k=k)

        events = [
            e for e in self.indb.get_all_events()
            if getattr(e, "location", None) == location
        ]

        if mode == "fusion":
            fused = [e for e in events if getattr(e, "is_fused", False)]
            candidates = fused or events
            if not candidates:
                themes = ctx.get("themes") or ctx.get("token_pool") or ["void"]
                return random.sample(list(themes), k=min(2, len(themes)))
            pick = random.choice(candidates)
            anchor = list(getattr(pick, "raw_data_anchor", []) or [])
            return anchor[:5] if anchor else ["fused", "pattern"]

        # resonance_weighted — weight by fusion_count + random pick
        if not events:
            pool = list(ctx.get("token_pool") or ctx.get("themes") or [])
            if pool:
                k = min(random.randint(1, 3), len(pool))
                return random.sample(pool, k=k)
            return ["resonance", "void"]

        weights = [
            1.0 + float(getattr(e, "fusion_count", 0) or 0)
            for e in events
        ]
        pick = random.choices(events, weights=weights, k=1)[0]
        anchor = list(getattr(pick, "raw_data_anchor", []) or [])
        if not anchor:
            return ["echo", "trace"]
        k = min(random.randint(1, min(4, len(anchor))), len(anchor))
        return random.sample(anchor, k=k) if len(anchor) > k else anchor
