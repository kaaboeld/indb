"""What-if core path: base echo query → seed resolution → subwave+slice."""
import asyncio
import os

from core.cognitive_pipeline import run_from_resolution
from core.event import Event
from core.resonance_index import ResonanceIndex
from core.seed_resolver import resolve_seed
from services.what_if.base_runner import run_base_query


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


def test_what_if_echo_base_to_pipeline():
    os.environ["RESONANCE_GRAPH_ENABLED"] = "true"
    os.environ["RESONANCE_SEMANTIC_ENABLED"] = "false"
    anchor = Event(raw_data_anchor=["earth", "signal"], location="sol")
    ally = Event(raw_data_anchor=["earth", "rescue"], location="sol")
    kernel = _FakeKernel([anchor, ally])

    base = asyncio.run(
        run_base_query(
            kernel,
            "echo",
            {"seed_id": anchor.id, "radius": 0.2, "limit": 10},
        )
    )
    resolution = resolve_seed("echo", {"seed_id": anchor.id}, base)
    assert resolution.resolved
    assert resolution.seed_id == anchor.id

    pipeline = asyncio.run(
        run_from_resolution(
            kernel,
            resolution,
            what_if="rescue frequency",
            radius=0.2,
            limit=10,
        )
    )
    assert pipeline.subwave is not None
    assert pipeline.slice.seed_id == anchor.id
    assert pipeline.slice.what_if == "rescue frequency"
