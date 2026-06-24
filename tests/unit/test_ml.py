"""
Unit tests for ML services

Tests pattern recognition, embeddings, and emotion classification.
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from core.event import Event
from services.ml.pattern_recognition import PatternRecognizer, ML_AVAILABLE as PR_AVAILABLE
from services.ml.embeddings import SemanticEmbeddings, ML_AVAILABLE as EMB_AVAILABLE
from services.ml.emotion_classifier import EmotionClassifier, ML_AVAILABLE as EC_AVAILABLE


# Skip tests if ML libraries not installed
pytestmark = pytest.mark.skipif(
    not all([PR_AVAILABLE, EMB_AVAILABLE, EC_AVAILABLE]),
    reason="ML libraries not installed"
)


def test_pattern_recognizer():
    """Test pattern recognition with DBSCAN."""
    print("\n🧪 Test: Pattern Recognition")
    print("=" * 60)
    
    recognizer = PatternRecognizer(eps=0.5, min_samples=2)
    
    # Create burst pattern (3 events in 5 minutes)
    import time
    base_time = time.time()
    events = [
        Event(["test", "pattern"], "Lab", timestamp=base_time),
        Event(["test", "pattern", "burst"], "Lab", timestamp=base_time + 60),
        Event(["test", "pattern", "burst"], "Lab", timestamp=base_time + 120),
    ]
    
    analysis = recognizer.detect_patterns(events)
    
    print(f"Clusters found: {analysis['clusters']}")
    print(f"Anomalies: {analysis['anomalies']}")
    print(f"Patterns: {analysis['patterns']}")
    
    assert analysis['clusters'] >= 0
    assert analysis['total_events'] == 3
    print("✅ PASSED\n")


def test_semantic_embeddings():
    """Test semantic embeddings with sentence-transformers."""
    print("🧪 Test: Semantic Embeddings")
    print("=" * 60)
    
    embeddings = SemanticEmbeddings(model_name='all-MiniLM-L6-v2')
    
    # Test similar tokens
    tokens1 = ["bicycle", "speed", "fast"]
    tokens2 = ["bike", "velocity", "quick"]
    tokens3 = ["coffee", "morning", "calm"]
    
    sim_similar = embeddings.calculate_similarity(tokens1, tokens2)
    sim_different = embeddings.calculate_similarity(tokens1, tokens3)
    
    print(f"Similarity (bicycle/bike): {sim_similar:.3f}")
    print(f"Similarity (bicycle/coffee): {sim_different:.3f}")
    
    # Semantic similarity should be higher for similar concepts
    assert sim_similar > sim_different
    assert 0.0 <= sim_similar <= 1.0
    assert 0.0 <= sim_different <= 1.0
    
    print("✅ PASSED\n")


def test_emotion_classifier_fallback():
    """Test emotion classifier fallback (rule-based)."""
    print("🧪 Test: Emotion Classifier (Fallback)")
    print("=" * 60)
    
    classifier = EmotionClassifier()
    
    # Test without training (should use fallback)
    event = Event(["bicycle", "speed", "adrenaline"], "Amsterdam")
    context = {"mood": "High_Value", "location": "Amsterdam"}
    
    prediction = classifier.predict(event, context)
    
    print(f"Predicted emotion: {prediction['emotion']}")
    print(f"Confidence: {prediction['confidence']:.2f}")
    print(f"Method: {prediction['method']}")
    
    assert prediction['emotion'] in EmotionClassifier.EMOTIONS
    assert prediction['method'] == 'rule-based'
    assert 0.0 <= prediction['confidence'] <= 1.0
    
    print("✅ PASSED\n")


def test_emotion_classifier_training():
    """Test emotion classifier with training."""
    print("🧪 Test: Emotion Classifier (ML)")
    print("=" * 60)
    
    classifier = EmotionClassifier(n_estimators=50)
    
    # Create training data
    training_data = []
    for i in range(20):
        # High energy + High_Value = Joy
        event = Event(["speed", "adrenaline", "fast"], "City")
        training_data.append({
            'event': event,
            'context': {'mood': 'High_Value', 'location': 'City'},
            'emotion': 'Joy'
        })
        
        # High energy + Fear = Anxiety
        event = Event(["speed", "danger", "threat"], "City")
        training_data.append({
            'event': event,
            'context': {'mood': 'Fear', 'location': 'City'},
            'emotion': 'Anxiety'
        })
    
    # Train
    metrics = classifier.train(training_data)
    
    print(f"Train accuracy: {metrics['train_accuracy']:.2f}")
    print(f"Test accuracy: {metrics['test_accuracy']:.2f}")
    print(f"Training samples: {metrics['training_samples']}")
    
    # Test prediction
    test_event = Event(["speed", "adrenaline"], "City")
    test_context = {'mood': 'High_Value', 'location': 'City'}
    
    prediction = classifier.predict(test_event, test_context)
    
    print(f"\nPredicted emotion: {prediction['emotion']}")
    print(f"Confidence: {prediction['confidence']:.2f}")
    print(f"Method: {prediction['method']}")
    
    assert classifier.is_trained
    assert prediction['method'] == 'ml'
    assert metrics['train_accuracy'] > 0.5
    
    print("✅ PASSED\n")


def test_embeddings_caching():
    """Test embeddings caching."""
    print("🧪 Test: Embeddings Caching")
    print("=" * 60)
    
    embeddings = SemanticEmbeddings()
    
    tokens = ["test", "cache", "performance"]
    
    # First call - should cache
    emb1 = embeddings.get_embedding(tokens)
    cache_size_1 = embeddings.cache_size()
    
    # Second call - should use cache
    emb2 = embeddings.get_embedding(tokens)
    cache_size_2 = embeddings.cache_size()
    
    print(f"Cache size after first call: {cache_size_1}")
    print(f"Cache size after second call: {cache_size_2}")
    print(f"Embeddings identical: {(emb1 == emb2).all()}")
    
    assert cache_size_1 == 1
    assert cache_size_2 == 1
    assert (emb1 == emb2).all()
    
    print("✅ PASSED\n")


def run_all_tests():
    """Run all ML tests."""
    print("\n" + "=" * 60)
    print("🚀 ML Services Test Suite")
    print("=" * 60)
    
    if not all([PR_AVAILABLE, EMB_AVAILABLE, EC_AVAILABLE]):
        print("\n⚠️  ML libraries not installed!")
        print("Install with: pip install scikit-learn sentence-transformers")
        return 1
    
    try:
        test_pattern_recognizer()
        test_semantic_embeddings()
        test_emotion_classifier_fallback()
        test_emotion_classifier_training()
        test_embeddings_caching()
        
        print("=" * 60)
        print("🎉 All ML tests passed!")
        print("=" * 60)
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
