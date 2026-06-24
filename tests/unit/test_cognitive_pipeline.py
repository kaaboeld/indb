"""Subwave → Slice pipeline."""
import asyncio
import os

from core.cognitive_pipeline import run_subwave_then_slice
from core.event import Event
from core.resonance_index import ResonanceIndex
from core.seed_resolver import SeedResolution


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


def test_pipeline_subwave_then_slice():
    os.environ["RESONANCE_GRAPH_ENABLED"] = "true"
    os.environ["RESONANCE_SEMANTIC_ENABLED"] = "false"
    anchor = Event(raw_data_anchor=["earth", "signal"], location="sol")
    other = Event(raw_data_anchor=["earth", "rescue"], location="sol")
    kernel = _FakeKernel([anchor, other])
    result = asyncio.run(
        run_subwave_then_slice(
            kernel,
            seed_id=anchor.id,
            what_if="rescue frequency aligns all nodes",
            radius=0.2,
            slice_limit=10,
        )
    )
    assert result.subwave is not None
    assert result.slice.seed_id == anchor.id
    assert "Subwave" in result.slice.logic
    assert len(result.slice.edges) >= 0
