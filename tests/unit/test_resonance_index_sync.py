"""Resonance index rebuild on memory compaction."""
from core.event import Event
from core.memory import MemoryManager
from core.resonance_index import ResonanceIndex


def test_compaction_rebuilds_index():
    idx = ResonanceIndex()
    rebuilt = {"count": 0}

    def on_compact():
        rebuilt["count"] += 1
        idx.rebuild(memory)

    memory = MemoryManager(capacity=5, pruning_threshold=0.6, on_compaction=on_compact)
    for i in range(8):
        memory.add(Event(raw_data_anchor=[f"t{i}"], location="loc"))
    assert rebuilt["count"] >= 1
    assert len(idx._event_tokens) <= len(memory)
