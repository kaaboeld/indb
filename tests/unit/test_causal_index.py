"""Causal temporal links."""
import os

from core.event import Event
from core.causal_index import CausalIndex


def test_temporal_chain_same_location():
    os.environ["CAUSAL_INDEX_ENABLED"] = "true"
    idx = CausalIndex()
    a = Event(raw_data_anchor=["a"], location="hall", timestamp=1000.0)
    b = Event(raw_data_anchor=["b"], location="hall", timestamp=1100.0)
    c = Event(raw_data_anchor=["c"], location="hall", timestamp=100000.0)
    idx.rebuild([a, b, c])
    after_a = idx.links_after(a.id)
    assert any(row["target_id"] == b.id for row in after_a)
    before_b = idx.links_before(b.id)
    assert any(row["target_id"] == a.id for row in before_b)
    assert c.id not in idx.neighbor_ids(a.id)
