"""A weak sleeper fades the edge. The edge stays. A heavy sleeper holds it."""
import os
import time

from core.echo import ResonanceResult
from core.event import Event
from core.indb import INDB
from core.memory import MemoryManager
from core.resonance_graph import ResonanceGraph
from core.resonance_index import ResonanceIndex
from storage.cold_store import ColdStore
import threading


def _enable_graph():
    os.environ["RESONANCE_GRAPH_ENABLED"] = "true"


def _link(graph, seed_id, target_id, score=0.95, age_sec=0):
    graph.record_wave(
        seed_id,
        [ResonanceResult(event_id=target_id, score=score, harmonic_type="direct", reason="bench")],
    )
    if age_sec:
        graph._edges[seed_id][0]["ts"] = time.time() - age_sec


def test_weak_sleeper_fades_the_edge_and_keeps_it(tmp_path, monkeypatch):
    monkeypatch.setattr("storage.cold_store.COLD_FILE", str(tmp_path / "cold.bin"))
    _enable_graph()
    sleeper = Event(
        raw_data_anchor=["noise", "000"],
        location="bench:volume/noise",
        timestamp=time.time() - 10 * 86400,
    )
    cold = ColdStore()
    cold.add([sleeper])
    restored = ColdStore()
    restored.load()
    assert sleeper.id in restored.salience_map()
    assert restored.salience_map()[sleeper.id] < 0.05
    graph = ResonanceGraph({})
    graph.bind_salience(restored.salience_map)
    _link(graph, "seed-hot", sleeper.id)

    assert graph.fade() == 1
    assert graph.fade() == 0
    assert sleeper.id not in graph.neighbor_ids("seed-hot")
    kept = graph.get_edges("seed-hot", include_stale=True)
    assert kept[0]["target_id"] == sleeper.id
    assert kept[0]["stale"] is True
    assert graph.stats()["edge_count"] == 1
    assert graph.stats()["stale_edges"] == 1
    assert sleeper.id in cold.salience_map()
    assert "_events" not in vars(cold)


def test_heavy_sleeper_holds_the_edge_past_the_clock(tmp_path, monkeypatch):
    monkeypatch.setattr("storage.cold_store.COLD_FILE", str(tmp_path / "cold.bin"))
    _enable_graph()
    sleeper = Event(
        raw_data_anchor=["law:heuristic", "mass:anchor"],
        location="bench:volume/axiom",
        timestamp=time.time() - 40 * 86400,
        fusion_count=2000,
        temporal_metadata={"last_touch": time.time()},
    )
    cold = ColdStore()
    cold.add([sleeper])
    graph = ResonanceGraph({})
    graph.bind_salience(cold.salience_map)
    _link(graph, "seed-hot", sleeper.id, age_sec=30 * 86400)

    assert sleeper.id in graph.neighbor_ids("seed-hot", min_score=0.9)
    assert graph.get_edges("seed-hot")[0]["held"] is True


def test_hot_edge_still_fades_on_the_clock():
    _enable_graph()
    graph = ResonanceGraph({})
    _link(graph, "seed-hot", "still-hot", age_sec=30 * 86400)
    assert graph.neighbor_ids("seed-hot") == []
    assert graph.get_edges("seed-hot", include_stale=True)


class _Host:
    def __init__(self):
        self.cold = ColdStore()
        self.memory = MemoryManager(capacity=50)
        self.resonance_index = ResonanceIndex()
        self.resonance_graph = ResonanceGraph({})
        self.lock = threading.Lock()
        self.persisted = 0
        self.wake_candidates = INDB.wake_candidates.__get__(self, _Host)
        self._wake = INDB._wake.__get__(self, _Host)

    def _persist(self):
        self.persisted += 1


def test_faded_edge_does_not_wake_and_a_held_edge_does(tmp_path, monkeypatch):
    monkeypatch.setattr("storage.cold_store.COLD_FILE", str(tmp_path / "cold.bin"))
    _enable_graph()
    host = _Host()
    weak = Event(
        raw_data_anchor=["noise", "only"],
        location="bench:volume/noise",
        timestamp=time.time() - 10 * 86400,
    )
    heavy = Event(
        raw_data_anchor=["law:heuristic", "mass:anchor"],
        location="bench:volume/axiom",
        timestamp=time.time() - 40 * 86400,
        fusion_count=2000,
        temporal_metadata={"last_touch": time.time()},
    )
    host.cold.add([weak, heavy])
    host.resonance_graph.bind_salience(host.cold.salience_map)
    _link(host.resonance_graph, "seed-weak", weak.id, score=0.99)
    _link(host.resonance_graph, "seed-heavy", heavy.id, score=0.95, age_sec=30 * 86400)

    quiet = Event(raw_data_anchor=["unrelated", "seed"], location="elsewhere")
    quiet.id = "seed-weak"
    assert host.wake_candidates(quiet) == []
    assert host.cold.contains(weak.id)

    cue = Event(raw_data_anchor=["unrelated", "cue"], location="elsewhere")
    cue.id = "seed-heavy"
    assert host.wake_candidates(cue) == [heavy.id]
    assert not host.cold.contains(heavy.id)
