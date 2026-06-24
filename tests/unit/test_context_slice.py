"""Unit tests for horizontal context slice."""
from core.event import Event
from core.resonance_index import ResonanceIndex
from core.context_slice import extract_factors, apply_horizontal_shift
from core.echo import ResonanceResult


def test_extract_factors_strips_what_if_prefix():
    factors = extract_factors("what if today I meet the girl of my dreams")
    assert "today" in factors or "meet" in factors
    assert "girl" in factors or "dreams" in factors


def test_resonance_index_candidates():
    idx = ResonanceIndex()
    a = Event(raw_data_anchor=["door", "sticker"], location="oasis/hall")
    b = Event(raw_data_anchor=["neighbor", "iq"], location="oasis/hall")
    c = Event(raw_data_anchor=["unrelated"], location="elsewhere")
    idx.index(a)
    idx.index(b)
    idx.index(c)
    candidates = idx.candidate_ids(a)
    assert b.id in candidates
    assert c.id not in candidates


def test_horizontal_shift_boosts_overlap():
    e1 = Event(raw_data_anchor=["dream", "girl"], location="x")
    cloud = [ResonanceResult(event_id=e1.id, score=0.4, harmonic_type="mixed", reason="")]
    edges = apply_horizontal_shift(cloud, ["dream", "girl"], lambda eid: e1 if eid == e1.id else None)
    assert len(edges) == 1
    assert edges[0].shifted_score > edges[0].base_score
    assert "dream" in edges[0].matched_factors
