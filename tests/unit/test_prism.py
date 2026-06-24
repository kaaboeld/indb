
import pytest
from core.prism import PrismEngine, PrismResult, MeaningVector
from core.echo import ResonanceResult
from core.event import Event

class MockINDB:
    def __init__(self, events):
        self.events = {e.id: e for e in events}
    
    def get_event(self, event_id):
        return self.events.get(event_id)

@pytest.fixture
def mock_events():
    return [
        Event(
            id="evt_thursday_generic",
            raw_data_anchor=["thursday", "evening", "boring"],
            location="home",
            source_id="system",
            fusion_count=1,
            timestamp=1000
        ),
        Event(
            id="evt_guinness_special",
            raw_data_anchor=["guinness", "dostoevsky", "pub"], # No "thursday" text!
            location="pub",
            source_id="user_A", # Owned by user
            fusion_count=1000,    # High Mass (Collective/Repetitive truth)
            timestamp=1000
        ),
        Event(
            id="evt_random",
            raw_data_anchor=["cat", "food"],
            location="kitchen",
            source_id="user_B",
            fusion_count=1,
            timestamp=1000
        )
    ]

@pytest.fixture
def prism_engine(mock_events):
    indb = MockINDB(mock_events)
    return PrismEngine(indb)

def test_prism_prioritizes_identity_and_mass(prism_engine):
    """
    Scenario: User_A asks for "Thursday".
    Echo returns 3 events.
    1. Generic Thursday (Direct match, low mass, system owner)
    2. Guinness (Resonant match via Echo, high mass, User_A owner)
    3. Random (Low match)
    
    Prism should pick #2 because:
    - Mass is high (50)
    - Identity matches User_A (Multiplier 2.0)
    - Resonance is high (Simulated)
    """
    
    # Simulate Echo Output (Echo creates the cloud, Prism filters it)
    resonance_cloud = [
        ResonanceResult(event_id="evt_thursday_generic", score=0.9, harmonic_type="direct", reason="Direct Match"),
        ResonanceResult(event_id="evt_guinness_special", score=0.8, harmonic_type="emotional", reason="Nostalgia"), # Lower resonance than direct, but...
        ResonanceResult(event_id="evt_random", score=0.1, harmonic_type="none", reason="Noise")
    ]
    
    # Calculate Scores Estimate:
    # 1. Generic: Mass(1->1.0) * Res(0.9) * Identity(0.5 system) = 0.45
    # 2. Guinness: Mass(50->1+ln(50)~4.9) * Res(0.8) * Identity(2.0 owner) = 4.9 * 0.8 * 2.0 = ~7.84 !
    # 3. Random: Mass(1->1.0) * Res(0.1) * Identity(0.5) = 0.05
    
    result = prism_engine.synthesize(
        query="Thursday evening",
        identity_key="user_A",
        resonance_cloud=resonance_cloud
    )
    
    assert result is not None
    assert result.event.id == "evt_guinness_special"
    assert result.meaning.context_label == "Subjective Reality"
    assert "Deeply Personal" in result.meaning.insight
    assert "Collective Truth" in result.meaning.insight # Due to high mass

def test_prism_paradox_detection(prism_engine):
    """
    Perception Paradox scenario:
    Two events with nearly equal scores but different context_labels.
    - evt_thursday_generic: owned by "system" → alignment=1.0 → "Objective Data"
    - evt_guinness_special: owned by "conflict_user" (not the querier) → alignment=1.0 → "Objective Data"
    Both get the same label. Now test with an event that produces a different label.
    
    We simulate a case where identity_key is deliberately set so the scores are
    very close AND labels diverge → expect is_paradoxical=True and perception_gap > 0.
    """
    from core.event import Event
    from core.prism import PrismEngine
    from core.echo import ResonanceResult

    events = [
        Event(
            id="evt_personal",
            raw_data_anchor=["signal", "deep"],
            location="private",
            source_id="user_paradox",  # owner → alignment=2.0 → "Subjective Reality"
            fusion_count=1,
        ),
        Event(
            id="evt_global",
            raw_data_anchor=["signal", "deep"],
            location="public",
            source_id="other",  # not owner → alignment=1.0 → "Objective Data"
            fusion_count=1,
        ),
    ]
    indb = type("INDB", (), {"get_event": lambda self, eid: {e.id: e for e in events}.get(eid)})()
    engine = PrismEngine(indb)

    # Scores are designed to be very close: same resonance, same mass (fusion_count=1)
    # Personal: (1.0 * 0.85) * 2.0 = 1.70 → "Subjective Reality"
    # Global:   (1.0 * 0.80) * 1.0 = 0.80 → "Objective Data"
    # score_proximity = 1 - |1.70 - 0.80| / 1.70 ≈ 0.47
    # label_divergence = 1.0 (different labels)
    # perception_gap ≈ 0.47 → is_paradoxical = True
    resonance_cloud = [
        ResonanceResult(event_id="evt_personal", score=0.85, harmonic_type="direct", reason="Match"),
        ResonanceResult(event_id="evt_global",   score=0.80, harmonic_type="direct", reason="Match"),
    ]

    result = engine.synthesize(query="signal deep", identity_key="user_paradox", resonance_cloud=resonance_cloud)

    assert result is not None
    assert result.event.id == "evt_personal"
    assert result.meaning.context_label == "Subjective Reality"
    assert len(result.alternative_readings) == 1
    assert result.alternative_readings[0].context_label == "Objective Data"
    assert result.perception_gap > 0.0
    assert result.is_paradoxical is True


def test_prism_no_paradox_when_scores_far_apart(prism_engine):
    """
    When one candidate dominates clearly, perception_gap ≈ 0 and is_paradoxical=False.
    """
    resonance_cloud = [
        ResonanceResult(event_id="evt_guinness_special", score=0.99, harmonic_type="emotional", reason="Dominant"),
        ResonanceResult(event_id="evt_thursday_generic", score=0.01, harmonic_type="none", reason="Noise"),
    ]
    result = prism_engine.synthesize(
        query="pub",
        identity_key="user_A",
        resonance_cloud=resonance_cloud
    )
    assert result is not None
    assert result.is_paradoxical is False
    assert result.perception_gap < 0.25


def test_prism_has_unread_essence_when_blind_payload_present():
    """
    If the winning event has a blind_payload, has_unread_essence=True.
    The system interprets the anchor but the actual essence is opaque.
    """
    from core.event import Event
    from core.prism import PrismEngine
    from core.echo import ResonanceResult

    event = Event(
        id="evt_blind",
        raw_data_anchor=["maybe", "safe"],
        location="unknown",
        source_id="x",
        fusion_count=1,
        blind_payload="hidden truth here",
    )
    indb = type("INDB", (), {"get_event": lambda self, eid: event if eid == "evt_blind" else None})()
    engine = PrismEngine(indb)
    resonance_cloud = [ResonanceResult(event_id="evt_blind", score=0.9, harmonic_type="direct", reason="x")]

    result = engine.synthesize(query="maybe", identity_key="x", resonance_cloud=resonance_cloud)

    assert result is not None
    assert result.has_unread_essence is True


def test_prism_anonymous_fallback(prism_engine):
    """
    If user is anonymous (None), identity alignment is neutral.
    High mass should still win, but score lower overall.
    """
    resonance_cloud = [
        ResonanceResult(event_id="evt_thursday_generic", score=0.9, harmonic_type="direct", reason="Direct Match"),
        ResonanceResult(event_id="evt_guinness_special", score=0.8, harmonic_type="emotional", reason="Nostalgia")
    ]
    
    # 1. Generic: 1.0 * 0.9 * 0.5 = 0.45
    # 2. Guinness: 4.9 * 0.8 * 0.5 = 1.96
    
    result = prism_engine.synthesize(
        query="Thursday evening",
        identity_key=None, # Anon
        resonance_cloud=resonance_cloud
    )
    
    assert result.event.id == "evt_guinness_special"
    assert "Deeply Personal" not in result.meaning.insight # Should NOT be deeply personal
    assert result.meaning.context_label == "Objective Data" # Or Subjective if alignment > 1.0? 
    # With anon, alignment is 0.5. So score < 1.0 (unless Mass is huge). 
    # Logic in code: context_label="Subjective" if alignment > 1.0. Anon alignment is 0.5. So "Objective Data".
