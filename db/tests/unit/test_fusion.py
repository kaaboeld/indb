"""
Event Fusion Tests

Test suite for Event Fusion system.
"""

import os
import sys
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core.event import Event
from services.fusion import EventFusion, FusedEvent


def test_similarity_calculation():
    """Test similarity calculation between events"""
    print("\n🧪 Test 1: Similarity Calculation")
    print("=" * 60)
    
    fusion = EventFusion()
    
    # Identical events
    event1 = Event(["bicycle", "speed"], "Amsterdam", timestamp=time.time())
    event2 = Event(["bicycle", "speed"], "Amsterdam", timestamp=time.time())
    
    similarity = fusion.calculate_similarity(event1, event2)
    print(f"Identical events: {similarity:.3f}")
    assert similarity > 0.95, f"Expected >0.95, got {similarity}"
    
    # Very similar events
    event3 = Event(["bicycle", "speed", "adrenaline"], "Amsterdam", timestamp=time.time())
    similarity = fusion.calculate_similarity(event1, event3)
    print(f"Very similar events: {similarity:.3f}")
    assert 0.7 < similarity < 0.95, f"Expected 0.7-0.95, got {similarity}"
    
    # Different events
    event4 = Event(["train", "morning"], "Rotterdam", timestamp=time.time() - 86400)
    similarity = fusion.calculate_similarity(event1, event4)
    print(f"Different events: {similarity:.3f}")
    assert similarity < 0.5, f"Expected <0.5, got {similarity}"
    
    print("✅ PASSED\n")


def test_full_merge():
    """Test full merge strategy"""
    print("🧪 Test 2: Full Merge")
    print("=" * 60)
    
    fusion = EventFusion()
    
    event1 = Event(["bicycle", "speed"], "Amsterdam", timestamp=1000.0)
    event2 = Event(["bicycle", "speed", "adrenaline"], "Amsterdam", timestamp=1300.0)
    
    fused = fusion.full_merge(event1, event2)
    
    print(f"Original tokens: {event1.raw_data_anchor}")
    print(f"New tokens: {event2.raw_data_anchor}")
    print(f"Fused tokens: {fused.raw_data_anchor}")
    print(f"Fusion count: {fused.fusion_count}")
    print(f"Pattern: {fused.temporal_span['pattern']}")
    
    assert fused.fusion_count == 2, f"Expected count=2, got {fused.fusion_count}"
    assert "adrenaline" in fused.raw_data_anchor, "Missing token from fusion"
    assert fused.fusion_type == "full_merge"
    
    print("✅ PASSED\n")


def test_weighted_merge():
    """Test weighted merge strategy"""
    print("🧪 Test 3: Weighted Merge")
    print("=" * 60)
    
    fusion = EventFusion()
    
    event1 = Event(["work", "stress"], "Office", timestamp=1000.0)
    event2 = Event(["work", "stress", "anxiety"], "Office", timestamp=1100.0)
    
    fused = fusion.weighted_merge(event1, event2, similarity=0.85)
    
    print(f"Token weights: {fused.token_weights}")
    print(f"Fusion type: {fused.fusion_type}")
    
    assert fused.fusion_type == "weighted_merge"
    assert "work" in fused.token_weights
    assert fused.token_weights["work"] > fused.token_weights.get("anxiety", 0)
    
    print("✅ PASSED\n")


def test_pattern_detection():
    """Test pattern detection"""
    print("🧪 Test 4: Pattern Detection")
    print("=" * 60)
    
    fusion = EventFusion()
    
    # Burst pattern
    pattern = fusion._detect_pattern(occurrences=5, duration=1800)  # 5 events in 30 min
    print(f"Burst pattern: {pattern}")
    assert pattern == "burst"
    
    # Daily recurring (2 events over 4 hours = 2 hour interval)
    pattern = fusion._detect_pattern(occurrences=2, duration=14400)  # 4 hours
    print(f"Daily recurring: {pattern}")
    assert pattern == "daily_recurring"
    
    # One-time
    pattern = fusion._detect_pattern(occurrences=1, duration=0)
    print(f"One-time: {pattern}")
    assert pattern == "one-time"
    
    print("✅ PASSED\n")


def test_find_similar():
    """Test finding similar events"""
    print("🧪 Test 5: Find Similar Events")
    print("=" * 60)
    
    fusion = EventFusion()
    
    target = Event(["bicycle", "speed"], "Amsterdam", timestamp=1000.0)
    
    pool = [
        Event(["bicycle", "speed", "adrenaline"], "Amsterdam", timestamp=1100.0),
        Event(["bicycle", "slow"], "Amsterdam", timestamp=1200.0),
        Event(["train", "morning"], "Rotterdam", timestamp=2000.0),
    ]
    
    similar = fusion.find_similar_events(target, pool, threshold=0.5)
    
    print(f"Found {len(similar)} similar events:")
    for s in similar:
        print(f"  - Event {s['id'][:8]}: similarity={s['similarity']:.3f}")
    
    assert len(similar) >= 1, "Should find at least 1 similar event"
    assert similar[0]["similarity"] > 0.5
    
    print("✅ PASSED\n")


def test_fusion_strategy_selection():
    """Test automatic fusion strategy selection"""
    print("🧪 Test 6: Fusion Strategy Selection")
    print("=" * 60)
    
    fusion = EventFusion()
    
    # High similarity → full merge
    should_fuse, strategy = fusion.should_fuse(0.96)
    print(f"Similarity 0.96: {strategy}")
    assert strategy == "full_merge"
    
    # Medium similarity → weighted merge
    should_fuse, strategy = fusion.should_fuse(0.80)
    print(f"Similarity 0.80: {strategy}")
    assert strategy == "weighted_merge"
    
    # Low similarity → semantic link
    should_fuse, strategy = fusion.should_fuse(0.60)
    print(f"Similarity 0.60: {strategy}")
    assert strategy == "semantic_link"
    
    # Very low → no fusion
    should_fuse, strategy = fusion.should_fuse(0.30)
    print(f"Similarity 0.30: {strategy}")
    assert strategy == "none"
    
    print("✅ PASSED\n")


def test_serialization():
    """Test FusedEvent serialization"""
    print("🧪 Test 7: Serialization")
    print("=" * 60)
    
    fusion = EventFusion()
    
    event1 = Event(["test", "data"], "Location", timestamp=1000.0)
    event2 = Event(["test", "data", "extra"], "Location", timestamp=1100.0)
    
    fused = fusion.full_merge(event1, event2)
    
    # Serialize
    data = fused.to_dict()
    print(f"Serialized keys: {list(data.keys())}")
    
    # Deserialize
    restored = FusedEvent.from_dict(data)
    
    assert restored.fusion_count == fused.fusion_count
    assert restored.fusion_type == fused.fusion_type
    assert len(restored.raw_data_anchor) == len(fused.raw_data_anchor)
    
    print("✅ PASSED\n")


def run_all_tests():
    """Run all fusion tests"""
    print("\n" + "=" * 60)
    print("🚀 Event Fusion Test Suite")
    print("=" * 60)
    
    try:
        test_similarity_calculation()
        test_full_merge()
        test_weighted_merge()
        test_pattern_detection()
        test_find_similar()
        test_fusion_strategy_selection()
        test_serialization()
        
        print("=" * 60)
        print("🎉 All tests passed!")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
