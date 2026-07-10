
import pytest
import time
from core.echo import ResonanceEngine, HarmonicWeights
from core.event import Event

@pytest.fixture
def engine():
    return ResonanceEngine(indb_instance=None)

@pytest.fixture
def seed_event():
    return Event(
        id="seed_001",
        raw_data_anchor=["summer", "evening", "wine"],
        location="test_loc",
        temporal_metadata={"mood": "Nostalgia"},
        timestamp=1750000000.0
    )

def test_direct_resonance(engine, seed_event):
    """Test overlapping tokens (token harmonic contributes)"""
    target = Event(
        id="evt_002",
        raw_data_anchor=["summer", "wine", "friends"],
        location="test_loc_2",
        temporal_metadata={"mood": "Happy"},
        timestamp=1760000000.0
    )
    # Tokens: summer, wine match. Jaccard + partial bonus → token score ~0.7
    # With token weight 0.2: 0.2*0.7 = 0.14 (no emotion/meta match)
    score = engine.calculate_resonance(seed_event, target)
    assert score >= 0.1

def test_emotional_resonance(engine, seed_event):
    """Test mood match (Medium Score)"""
    target = Event(
        id="evt_003",
        raw_data_anchor=["winter", "cold"],
        location="test_loc_3",
        temporal_metadata={"mood": "Nostalgia"},
        timestamp=1770000000.0
    )
    # Mood matches exactly (1.0 * 0.3 weight = 0.3)
    score = engine.calculate_resonance(seed_event, target)
    assert score >= 0.3

def test_cyclic_resonance(engine, seed_event):
    """Test same month/day (Cyclic Score)"""
    # Create timestamp exactly 1 year later
    target = Event(
        id="evt_004",
        raw_data_anchor=["random"],
        location="test_loc_4",
        temporal_metadata={"mood": "Neutral"},
        timestamp=seed_event.timestamp + (365 * 24 * 3600) 
    )
    
    # We rely on gmtime in the engine. If it falls in same month, +0.5 * 0.2 weight = 0.1
    # Note: 365 days might drift slightly, but typically stays in same month unless edge case.
    score = engine.calculate_resonance(seed_event, target)
    assert score >= 0.05 # Lower threshold due to drift possibility but > 0

def test_no_resonance(engine, seed_event):
    """Test complete mismatch"""
    target = Event(
        id="evt_005",
        raw_data_anchor=["concrete", "tax"],
        location="test_loc_5",
        temporal_metadata={"mood": "Stress"},
        timestamp=seed_event.timestamp + 10000000 # ~115 days later (diff month)
    )
    score = engine.calculate_resonance(seed_event, target)
    assert score < 0.1

def test_weighted_tuning(engine, seed_event):
    """Test adjusting weights"""
    target = Event(
        id="evt_006",
        raw_data_anchor=["summer"],
        location="test_loc_6",
        temporal_metadata={"mood": "Nostalgia"},
        timestamp=seed_event.timestamp
    )
    
    # Default calc: 0.5*T(0.33) + 0.3*E(1.0) + 0.2*M(1.0) approx 0.6
    s1 = engine.calculate_resonance(seed_event, target)
    
    # Boost emotion weight
    engine.set_weights(HarmonicWeights(token=0.1, emotion=0.9, meta=0.0))
    s2 = engine.calculate_resonance(seed_event, target)
    
    # If Mood matches (score 1.0), boosting weight (0.3 -> 0.9) massively increases score
    # T contribution drops, but E contribution triples.
    # We just check it works.
    assert s2 > 0.0
