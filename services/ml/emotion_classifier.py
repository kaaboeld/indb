"""
Emotion Classification Service for INDB

ML-based emotion classification using RandomForest.
Learns from historical data to predict emotions based on context.
"""

from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from collections import Counter

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False


class EmotionClassifier:
    """
    ML-based emotion classifier for INDB.
    
    Learns patterns from historical interpretations to predict
    emotions based on token patterns and context.
    """
    
    # Emotion categories aligned with INDB concepts
    EMOTIONS = [
        "Joy", "Fear", "Curiosity", "Focus", 
        "Anxiety", "Suspicion", "Analysis", "Paranoia", "Neutral"
    ]
    
    def __init__(self, n_estimators: int = 100):
        """
        Initialize emotion classifier.
        
        """
        if ML_AVAILABLE:
            self.classifier = RandomForestClassifier(
                n_estimators=n_estimators,
                random_state=42,
                max_depth=10
            )
        else:
            self.classifier = None
            # raise ImportError("scikit-learn required for EmotionClassifier") - DISABLED for robustness
            print("WARN: EmotionClassifier running in rule-based fallback mode (no sklearn)", flush=True)
        self.is_trained = False
        self.feature_names = []
        self.token_vocabulary = set()
    
    def train(self, training_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Train classifier on historical data.
        
        Args:
            training_data: List of dicts with 'event', 'context', 'emotion'
            
        Returns:
            Training metrics
        """
        if len(training_data) < 10:
            raise ValueError("Need at least 10 training examples")
        
        # Extract features and labels
        X = []
        y = []
        
        for item in training_data:
            features = self._extract_features(item['event'], item['context'])
            X.append(features)
            y.append(item['emotion'])
            
            # Build vocabulary
            self.token_vocabulary.update(item['event'].raw_data_anchor)
        
        X = np.array(X)
        y = np.array(y)
        
        # Train-test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Train
        self.classifier.fit(X_train, y_train)
        self.is_trained = True
        
        # Evaluate
        train_score = self.classifier.score(X_train, y_train)
        test_score = self.classifier.score(X_test, y_test)
        
        return {
            'train_accuracy': float(train_score),
            'test_accuracy': float(test_score),
            'training_samples': len(training_data),
            'vocabulary_size': len(self.token_vocabulary)
        }
    
    def predict(
        self, 
        event: Any, 
        context: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Predict emotion for event given context.
        
        Args:
            event: Event object
            context: Context dictionary with 'mood', 'location', etc.
            
        Returns:
            Prediction with emotion and confidence
        """
        if not self.is_trained:
            return self._fallback_prediction(event, context)
        
        # Extract features
        features = self._extract_features(event, context)
        
        # Predict
        emotion = self.classifier.predict([features])[0]
        probabilities = self.classifier.predict_proba([features])[0]
        confidence = float(probabilities.max())
        
        # Get top 3 predictions
        top_indices = np.argsort(probabilities)[-3:][::-1]
        top_predictions = [
            {
                'emotion': self.classifier.classes_[idx],
                'probability': float(probabilities[idx])
            }
            for idx in top_indices
        ]
        
        return {
            'emotion': emotion,
            'confidence': confidence,
            'top_predictions': top_predictions,
            'method': 'ml'
        }
    
    def _extract_features(
        self, 
        event: Any, 
        context: Dict[str, str]
    ) -> np.ndarray:
        """
        Extract numerical features from event and context.
        
        Features:
        - Token count
        - Token diversity
        - Presence of high-energy tokens
        - Presence of negative tokens
        - Context mood encoding
        - Location match
        """
        # Token features
        tokens = event.raw_data_anchor
        token_count = len(tokens)
        unique_tokens = len(set(tokens))
        token_diversity = unique_tokens / token_count if token_count > 0 else 0
        
        # Energy detection (simple heuristic)
        high_energy_tokens = {'speed', 'fast', 'adrenaline', 'rush', 'intense'}
        has_high_energy = any(t in high_energy_tokens for t in tokens)
        
        # Negative valence detection
        negative_tokens = {'fear', 'anxiety', 'threat', 'danger', 'pain'}
        has_negative = any(t in negative_tokens for t in tokens)
        
        # Context features
        mood = context.get('mood', 'Neutral')
        mood_encoding = {
            'High_Value': 1.0,
            'Fear': -1.0,
            'Neutral': 0.0
        }.get(mood, 0.0)
        
        # Location match
        location_match = 1.0 if context.get('location') == event.location else 0.0
        
        return np.array([
            token_count,
            token_diversity,
            float(has_high_energy),
            float(has_negative),
            mood_encoding,
            location_match
        ])
    
    def _fallback_prediction(
        self, 
        event: Any, 
        context: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Rule-based fallback when ML model not trained.
        
        Uses INDB's original JIT interpretation logic.
        """
        tokens = event.raw_data_anchor
        mood = context.get('mood', 'Neutral')
        
        # Simple rule-based classification
        high_energy_tokens = {'speed', 'fast', 'adrenaline', 'rush', 'intense'}
        negative_tokens = {'fear', 'anxiety', 'threat', 'danger', 'pain'}
        
        has_high_energy = any(t in high_energy_tokens for t in tokens)
        has_negative = any(t in negative_tokens for t in tokens)
        
        # Interpretation matrix (simplified)
        if mood == 'High_Value':
            if has_high_energy:
                emotion = 'Joy'
            elif has_negative:
                emotion = 'Curiosity'
            else:
                emotion = 'Focus'
        elif mood == 'Fear':
            if has_high_energy:
                emotion = 'Anxiety'
            elif has_negative:
                emotion = 'Fear'
            else:
                emotion = 'Suspicion'
        else:  # Neutral
            emotion = 'Neutral'
        
        return {
            'emotion': emotion,
            'confidence': 0.7,  # Lower confidence for rule-based
            'top_predictions': [{'emotion': emotion, 'probability': 0.7}],
            'method': 'rule-based'
        }
    
    def get_feature_importance(self) -> Dict[str, float]:
        """
        Get feature importance scores.
        
        Returns:
            Dictionary mapping feature names to importance scores
        """
        if not self.is_trained:
            return {}
        
        feature_names = [
            'token_count',
            'token_diversity',
            'has_high_energy',
            'has_negative',
            'mood_encoding',
            'location_match'
        ]
        
        importances = self.classifier.feature_importances_
        
        return {
            name: float(importance)
            for name, importance in zip(feature_names, importances)
        }
