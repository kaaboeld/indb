import pytest
from services.fusion.engine import EventFusion

def test_tune_threshold_defaults():
    fusion = EventFusion()
    # Should start at default 0.75 (from changed code) or config 0.75. 
    # Actually init says 0.75. 
    assert fusion.config["threshold"] == 0.75
    
    # Normal metrics -> stable or drift to default
    metrics = {"cpu_percent": 10.0, "memory_percent": 10.0}
    fusion.tune_threshold(metrics)
    assert fusion.config["threshold"] == 0.75

def test_tune_threshold_high_cpu():
    fusion = EventFusion()
    initial = fusion.config["threshold"]
    
    # High CPU -> Increase threshold (stricter)
    metrics = {"cpu_percent": 90.0, "memory_percent": 10.0}
    
    new_th = fusion.tune_threshold(metrics)
    assert new_th > initial
    assert new_th <= 0.95
    assert fusion.config["threshold"] == new_th

def test_tune_threshold_high_memory():
    fusion = EventFusion()
    initial = fusion.config["threshold"]
    
    # High Mem, Low CPU -> Decrease threshold (aggressive)
    metrics = {"cpu_percent": 10.0, "memory_percent": 90.0}
    
    new_th = fusion.tune_threshold(metrics)
    assert new_th < initial
    assert new_th >= 0.60
    assert fusion.config["threshold"] == new_th

def test_tune_threshold_normalization():
    fusion = EventFusion()
    # Set to extreme
    fusion.config["threshold"] = 0.90
    
    # Normal metrics -> drift down to default (0.75)
    metrics = {"cpu_percent": 20.0, "memory_percent": 20.0}
    
    new_th = fusion.tune_threshold(metrics)
    assert new_th < 0.90
    
    # Set to low extreme
    fusion.config["threshold"] = 0.60
    new_th = fusion.tune_threshold(metrics)
    assert new_th > 0.60
