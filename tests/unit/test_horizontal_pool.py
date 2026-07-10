"""Horizontal candidate pool (graph + index + causal)."""
import os

from core.event import Event
from core.horizontal_pool import collect_candidate_ids
from core.resonance_index import ResonanceIndex
from core.resonance_graph import ResonanceGraph
from core.echo import ResonanceResult


class _FakeKernel:
    def __init__(self, events):
        self.db = self
        self._events = {e.id: e for e in events}
        self.resonance_graph = ResonanceGraph({})
        self.resonance_index = ResonanceIndex()
        self.causal_index = None
        for e in events:
            self.resonance_index.index(e)

    def get_event(self, event_id: str):
        return self._events.get(event_id)


def test_pool_unions_graph_and_index():
    os.environ["RESONANCE_SEMANTIC_ENABLED"] = "false"
    seed = Event(raw_data_anchor=["earth", "anchor"], location="sol")
    neighbor = Event(raw_data_anchor=["earth", "ally"], location="sol")
    distant = Event(raw_data_anchor=["mars"], location="mars")
    kernel = _FakeKernel([seed, neighbor, distant])
    kernel.resonance_graph.record_wave(
        seed.id,
        [ResonanceResult(event_id=neighbor.id, score=0.9, harmonic_type="strong", reason="")],
    )
    ids, mode = collect_candidate_ids(
        kernel, seed, radius=0.3, limit=20, resolve_event=kernel.get_event
    )
    assert neighbor.id in ids
    assert "graph" in mode or "index" in mode
