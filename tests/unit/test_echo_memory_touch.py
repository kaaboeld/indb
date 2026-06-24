"""Echo updates last_resonance_at on seed and ripples."""
import asyncio
import os
import time

from core.echo import ResonanceEngine
from core.event import Event
from core.resonance_index import ResonanceIndex


class _FakeKernel:
    def __init__(self, events):
        self.db = self
        self._events = {e.id: e for e in events}
        self.resonance_graph = __import__(
            "core.resonance_graph", fromlist=["ResonanceGraph"]
        ).ResonanceGraph({})
        self.resonance_index = ResonanceIndex()
        self.causal_index = None
        for e in events:
            self.resonance_index.index(e)

    def get_event(self, event_id: str):
        return self._events.get(event_id)

    def get_all_events(self):
        return list(self._events.values())


def test_echo_touches_resonance_metadata():
    os.environ["RESONANCE_SEMANTIC_ENABLED"] = "false"
    before = time.time() - 3600
    seed = Event(
        raw_data_anchor=["earth", "anchor"],
        location="sol",
        timestamp=before,
        temporal_metadata={},
    )
    ally = Event(raw_data_anchor=["earth", "ally"], location="sol", temporal_metadata={})
    kernel = _FakeKernel([seed, ally])
    engine = ResonanceEngine(kernel)
    asyncio.run(engine.resonate(seed.id, radius=0.2, limit=10))
    assert seed.temporal_metadata.get("last_resonance_at", 0) > before
