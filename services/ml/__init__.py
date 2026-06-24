"""
ML Services for INDB

Machine Learning integration for intelligent pattern recognition,
semantic similarity, and emotion classification.
"""

from services.ml.pattern_recognition import PatternRecognizer
from services.ml.embeddings import SemanticEmbeddings
from services.ml.emotion_classifier import EmotionClassifier

__all__ = ['PatternRecognizer', 'SemanticEmbeddings', 'EmotionClassifier']
