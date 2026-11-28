"""Memory salience math."""
import time

from core.event import Event
from core.memory_salience import compute_salience, is_hot, should_wake


def test_heavy_recent_event_is_hot():
    ev = Event(
        raw_data_anchor=["anchor"],
        location="x",
        timestamp=time.time(),
        fusion_count=10,
    )
    ev.temporal_metadata["last_resonance_at"] = time.time()
    assert is_hot(compute_salience(ev))


def test_source_weight_zero_zeroes_salience():
    ev = Event(
        raw_data_anchor=["anchor"],
        location="x",
        timestamp=time.time(),
        fusion_count=10,
        source_weight=0.0,
    )
    ev.temporal_metadata["last_resonance_at"] = time.time()
    assert compute_salience(ev) == 0.0
    assert not is_hot(compute_salience(ev))


def test_wake_thresholds():
    assert should_wake(echo_score=0.9)
    assert should_wake(lock_score=0.8)
    assert not should_wake(echo_score=0.1, lock_score=0.1)
