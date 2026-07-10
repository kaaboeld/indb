import time

from core.memory_touch import touch_resonance
from core.memory_salience import compute_salience
from core.event import Event


def test_touch_resonance_updates_metadata():
    ev = Event(
        id="a",
        timestamp=time.time() - 3600,
        location="x",
        raw_data_anchor=["seed"],
        temporal_metadata={},
    )
    before = compute_salience(ev)
    touch_resonance(ev)
    after = compute_salience(ev)
    assert ev.temporal_metadata.get("last_resonance_at")
    assert after >= before
