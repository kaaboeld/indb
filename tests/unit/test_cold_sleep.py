"""Sleep and wake: exhale keeps the event, a strong seed brings it back."""
import threading
import time

from core.event import Event
from core.indb import INDB
from core.memory import MemoryManager
from core.resonance_graph import ResonanceGraph
from core.resonance_index import ResonanceIndex
from storage.cold_store import ColdStore


def _old_event(tokens, **kwargs):
    event = Event(
        raw_data_anchor=tokens,
        location=kwargs.pop("location", "city/rotterdam"),
        timestamp=time.time() - 10 * 86400,
        **kwargs,
    )
    return event


def test_prune_sleeps_weak_events_and_keeps_the_axiom():
    slept = []
    memory = MemoryManager(capacity=10, pruning_threshold=0.5, on_sleep=slept.extend)
    axiom = _old_event(
        ["signed", "fact"],
        signature={"algorithm": "Ed25519", "signature": "proof"},
    )
    memory.add(axiom)
    for i in range(10):
        memory.add(_old_event(["noise", str(i)]))

    hot_ids = [event.id for event in memory]
    assert axiom.id in hot_ids
    assert axiom.id not in [event.id for event in slept]
    assert slept
    assert all(not getattr(event, "signature", None) for event in slept)


def test_cold_file_roundtrip_and_signed_events_stay_out(tmp_path, monkeypatch):
    path = str(tmp_path / "cold.bin")
    monkeypatch.setattr("storage.cold_store.COLD_FILE", path)

    original = ColdStore()
    sleeper = _old_event(["rotterdam", "rain", "night"])
    signed = _old_event(["axiom"], signature={"algorithm": "Ed25519", "signature": "proof"})
    original.add([sleeper, signed])

    restored = ColdStore()
    restored.load()

    assert restored.count == 1
    assert "_events" not in vars(restored)
    woken = restored.get(sleeper.id)
    assert woken is not None
    assert woken is not sleeper
    assert woken.raw_data_anchor == ["rotterdam", "rain", "night"]
    assert not restored.contains(signed.id)


class _Host:
    """Just enough of INDB for wake_candidates / _wake."""

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


def test_identical_seed_wakes_the_sleeper(tmp_path, monkeypatch):
    monkeypatch.setattr("storage.cold_store.COLD_FILE", str(tmp_path / "cold.bin"))
    host = _Host()
    sleeper = _old_event(["rotterdam", "rain", "night"])
    host.cold.add([sleeper])

    seed = Event(raw_data_anchor=["rotterdam", "rain", "night"], location="city/rotterdam")
    woken = host.wake_candidates(seed)

    assert woken == [sleeper.id]
    assert any(event.id == sleeper.id for event in host.memory)
    assert not host.cold.contains(sleeper.id)
    assert host.cold.wake_count == 1
    assert host.persisted == 1


def test_recall_by_id_does_not_depend_on_walking_the_stream():
    memory = MemoryManager(capacity=10, pruning_threshold=0.5)
    kept = _old_event(["kept", "anchor"], fusion_count=10)
    kept.temporal_metadata["last_resonance_at"] = time.time()
    memory.add(kept)
    weak = [_old_event(["noise", str(i)]) for i in range(10)]
    for event in weak:
        memory.add(event)

    assert memory.get(kept.id) is kept
    assert memory.get("missing") is None
    for event in weak:
        if event.id not in [item.id for item in memory]:
            assert memory.get(event.id) is None


def test_replacing_an_event_moves_the_id():
    memory = MemoryManager()
    original = _old_event(["first"])
    memory.add(original)
    replacement = _old_event(["second"])
    memory[0] = replacement
    assert memory.get(original.id) is None
    assert memory.get(replacement.id) is replacement


def test_weak_overlap_leaves_the_sleeper_cold(tmp_path, monkeypatch):
    monkeypatch.setattr("storage.cold_store.COLD_FILE", str(tmp_path / "cold.bin"))
    host = _Host()
    sleeper = _old_event(["rotterdam", "rain", "night", "canal"])
    host.cold.add([sleeper])

    seed = Event(raw_data_anchor=["sun"], location="desert")
    assert host.wake_candidates(seed) == []
    assert host.cold.contains(sleeper.id)
    assert host.cold.wake_count == 0
