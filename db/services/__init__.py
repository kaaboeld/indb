"""
Services layer for INDB

Business logic modules organized by domain.
"""

# Fusion services
from services.fusion.engine import EventFusion, FusedEvent
from services.fusion.analytics import get_fusion_stats

# Temporal services
from services.temporal.parser import TemporalParser

# Interpretation services
from services.interpretation.emotional_firewall import EmotionalFirewall

# ML services (optional - graceful degradation if not installed)
try:
    from services.ml.pattern_recognition import PatternRecognizer
    from services.ml.embeddings import SemanticEmbeddings
    from services.ml.emotion_classifier import EmotionClassifier
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    PatternRecognizer = None
    SemanticEmbeddings = None
    EmotionClassifier = None

__all__ = [
    'EventFusion',
    'FusedEvent',
    'get_fusion_stats',
    'TemporalParser',
    'EmotionalFirewall',
    'PatternRecognizer',
    'SemanticEmbeddings',
    'EmotionClassifier',
    'ML_AVAILABLE'
]
