"""Subwave unified broadcast."""
import asyncio
import os

from core.event import Event
from core.resonance_index import ResonanceIndex
from core.subwave import SubwaveEngine


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

    def iter_events(self):
        return iter(self._events.values())


def test_subwave_locks_aligned_nodes():
    os.environ["RESONANCE_GRAPH_ENABLED"] = "true"
    os.environ["RESONANCE_SEMANTIC_ENABLED"] = "false"
    anchor = Event(raw_data_anchor=["earth", "tardis", "anchor"], location="sol/earth")
    ally = Event(raw_data_anchor=["earth", "rescue", "signal"], location="sol/earth")
    noise = Event(raw_data_anchor=["mars", "dust"], location="mars")
    kernel = _FakeKernel([anchor, ally, noise])
    engine = SubwaveEngine(kernel)
    result = asyncio.run(
        engine.broadcast(anchor.id, modifier="rescue frequency", lock_threshold=0.25)
    )
    locked_ids = {n.event_id for n in result.locked_nodes}
    assert ally.id in locked_ids
    assert result.coherence > 0
    assert result.anchor.anchor_id == anchor.id
