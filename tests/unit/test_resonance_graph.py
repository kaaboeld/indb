"""Materialized resonance graph."""
import os

from core.event import Event
from core.echo import ResonanceEngine, ResonanceResult
from core.resonance_graph import ResonanceGraph


class _FakeKernel:
    def __init__(self, events):
        self.db = self
        self._events = {e.id: e for e in events}
        self.resonance_graph = ResonanceGraph({})
        self.resonance_index = None

    def get_event(self, event_id: str):
        return self._events.get(event_id)

    def get_all_events(self):
        return list(self._events.values())

    def iter_events(self):
        return iter(self._events.values())


import asyncio


def test_record_and_neighbor_lookup():
    os.environ["RESONANCE_GRAPH_ENABLED"] = "true"
    os.environ["RESONANCE_SEMANTIC_ENABLED"] = "false"
    a = Event(raw_data_anchor=["door", "sticker"], location="hall")
    b = Event(raw_data_anchor=["door", "neighbor"], location="hall")
    c = Event(raw_data_anchor=["sky"], location="outside")
    kernel = _FakeKernel([a, b, c])
    kernel.resonance_index = __import__(
        "core.resonance_index", fromlist=["ResonanceIndex"]
    ).ResonanceIndex()
    for e in [a, b, c]:
        kernel.resonance_index.index(e)

    engine = ResonanceEngine(kernel)
    ripples = asyncio.run(engine.resonate(a.id, radius=0.2, limit=10))
    assert any(r.event_id == b.id for r in ripples)
    assert b.id in kernel.resonance_graph.neighbor_ids(a.id, min_score=0.2)
