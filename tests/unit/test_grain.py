"""
Unit tests for Grain (identity tolerance spectrum).
"""

import pytest

from core.echo import ResonanceEngine
from core.event import Event
from core.grain.engine import GrainEngine
from core.grain.exact import verify_exact
from core.grain.models import GrainConfig, GrainTier
from core.grain.redundant import verify_redundant
from core.grain.resonant import verify_resonant
from core.grain.statistical import build_distribution, verify_statistical
from core.signing import sign_event
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


@pytest.fixture
def private_key():
    return Ed25519PrivateKey.generate()


@pytest.fixture
def signed_event(private_key):
    event = {
        "id": "evt-grain-001",
        "timestamp": 1750000000.0,
        "raw_data_anchor": ["truth", "sensor", "heartbeat"],
        "location": "system/core",
        "ttl": 86400,
    }
    event["signature"] = sign_event(event, private_key)
    return event


@pytest.fixture
def seed_event():
    return Event(
        id="seed_001",
        raw_data_anchor=["summer", "evening", "wine", "memory"],
        location="books/test",
        temporal_metadata={"mood": "Nostalgia"},
    )


class FakeINDB:
    def __init__(self, events):
        self._events = {e.id: e for e in events}
        self.source_registry = {}

    def get_event(self, event_id):
        return self._events.get(event_id)

    def iter_events(self):
        return iter(self._events.values())


def test_exact_verified(signed_event):
    result = verify_exact(signed_event)
    assert result.tier_used == GrainTier.EXACT
    assert result.verdict == "verified"
    assert result.match_score == 1.0
    assert result.key_id is not None


def test_exact_unsigned_rejected():
    event = {
        "id": "unsigned",
        "raw_data_anchor": ["a", "b"],
        "location": "test",
    }
    result = verify_exact(event)
    assert result.verdict == "rejected"


def test_exact_wrong_key_id(signed_event):
    result = verify_exact(signed_event, expected_key_id="0" * 64)
    assert result.verdict == "rejected"


def test_resonant_match(seed_event):
    candidate = Event(
        id="cand_001",
        raw_data_anchor=["summer", "wine", "friends"],
        location="books/other",
    )
    engine = ResonanceEngine(None)
    result = verify_resonant(seed_event, candidate, engine, reputation=0.8)
    assert result.tier_used == GrainTier.RESONANT
    assert result.match_score > 0.0
    assert result.verdict in ("likely_same_origin", "rejected")


def test_resonant_strict_tolerance_rejects(seed_event):
    candidate = Event(
        id="cand_002",
        raw_data_anchor=["concrete", "tax"],
        location="nowhere",
    )
    engine = ResonanceEngine(None)
    strict = GrainConfig(tolerance=0.0)
    result = verify_resonant(seed_event, candidate, engine, reputation=0.3, config=strict)
    assert result.verdict == "rejected"


def test_redundant_cluster(signed_event, private_key):
    events = [signed_event]
    for i in range(2, 5):
        ev = {
            "id": f"evt-grain-{i:03d}",
            "timestamp": 1750000000.0 + i,
            "raw_data_anchor": ["truth", "sensor"],
            "location": "system/core",
        }
        ev["signature"] = sign_event(ev, private_key)
        events.append(ev)

    result = verify_redundant(events, expected_key_id=signed_event["signature"]["key_id"])
    assert result.tier_used == GrainTier.REDUNDANT
    assert result.verdict == "verified"
    assert result.events_valid == 4
    assert result.events_total == 4


def test_redundant_insufficient_events(signed_event):
    result = verify_redundant([signed_event], config=GrainConfig(min_events=3))
    assert result.verdict == "insufficient_signal"
    assert result.insufficient_signal is True


def test_statistical_match():
    ref_events = [
        Event(
            id=f"ref_{i}",
            raw_data_anchor=["memory", "truth", "signal", "pattern"] * 5,
            location="source/a",
        )
        for i in range(3)
    ]
    candidate = Event(
        id="cand",
        raw_data_anchor=["memory", "truth", "signal", "pattern"] * 3,
        location="source/a",
    )
    result = verify_statistical(ref_events, candidate, config=GrainConfig(min_tokens=20))
    assert result.tier_used == GrainTier.STATISTICAL
    assert result.tokens_observed >= 12
    assert result.p_value is not None


def test_statistical_insufficient_tokens():
    ref_events = [Event(id="r1", raw_data_anchor=["a", "b"], location="x")]
    candidate = Event(id="c1", raw_data_anchor=["a"], location="x")
    result = verify_statistical(ref_events, candidate)
    assert result.verdict == "insufficient_signal"


def test_build_distribution():
    events = [
        Event(id="1", raw_data_anchor=["hello", "world", "hello"], location="x"),
        Event(id="2", raw_data_anchor=["world", "test"], location="x"),
    ]
    dist = build_distribution(events, n=2)
    assert sum(dist.values()) >= 2


def test_engine_auto_exact(signed_event, seed_event):
    indb = FakeINDB([seed_event])
    engine = GrainEngine(indb)
    result = engine.verify(candidate=signed_event)
    assert result.tier_used == GrainTier.EXACT
    assert result.verdict == "verified"


def test_engine_auto_resonant(seed_event):
    indb = FakeINDB([seed_event])
    engine = GrainEngine(indb)
    result = engine.verify(
        candidate={"raw_data_anchor": ["summer", "wine"], "location": "test"},
        reference_event_id="seed_001",
    )
    assert result.tier_used == GrainTier.RESONANT


def test_engine_select_tier():
    engine = GrainEngine(None)
    assert engine.select_tier({"signature": {"signature": "abc"}}) == GrainTier.EXACT
    assert engine.select_tier({"raw_data_anchor": ["a"]}) == GrainTier.RESONANT
