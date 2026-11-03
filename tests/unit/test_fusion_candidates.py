"""Inhale scores events that share a token. The rest of the life stays out of the pass."""
from core.event import Event
from core.indb import INDB
from core.memory import MemoryManager
from core.resonance_index import ResonanceIndex
from services.fusion.engine import EventFusion


class _Host:
    def __init__(self):
        self.memory = MemoryManager()
        self.resonance_index = ResonanceIndex()
        self.fusion_engine = EventFusion()
        self.fusion_engine.embeddings = None
        self._fusion_candidates = INDB._fusion_candidates.__get__(self, _Host)

    def keep(self, event):
        self.memory.add(event)
        self.resonance_index.index(event)
        return event


def test_shared_token_is_scored_and_disjoint_noise_is_not():
    host = _Host()
    partner = host.keep(Event(["bicycle", "speed"], "Amsterdam"))
    for i in range(40):
        host.keep(Event([f"noise:{i}"], f"bench/{i}"))

    incoming = Event(["bicycle", "speed"], "Rotterdam")
    pool = host._fusion_candidates(incoming)

    assert [event.id for event in pool] == [partner.id]
    similar = host.fusion_engine.find_similar_events(incoming, pool, threshold=0.5)
    assert similar
    assert similar[0]["id"] == partner.id


def test_embeddings_still_see_the_whole_hot_tier():
    host = _Host()
    host.fusion_engine.embeddings = object()
    host.keep(Event(["bicycle", "speed"], "Amsterdam"))
    host.keep(Event(["train"], "Rotterdam"))

    pool = host._fusion_candidates(Event(["sky"], "desert"))
    assert len(pool) == 2


def test_replace_updates_the_body_without_a_second_id():
    memory = MemoryManager()
    original = Event(["first"], "hall")
    memory.add(original)
    fused = Event(["first", "second"], "hall", id=original.id, fusion_count=2)

    assert memory.replace(fused) is True
    assert memory.get(original.id) is fused
    assert memory[0] is fused
    assert len(memory) == 1
    assert memory.replace(Event(["missing"], "hall", id="absent")) is False
