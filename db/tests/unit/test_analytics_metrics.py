
import pytest
import time
from unittest.mock import MagicMock
from core.analytics import INDBAnalytics

class TestAutonomousMetrics:
    """Test Autonomous Metrics (Health Score & OOM Prediction)."""
    
    def test_health_score_perfect(self):
        """Test perfect health score."""
        db_mock = MagicMock()
        analytics = INDBAnalytics(db_mock)
        
        # Inject perfect history
        analytics.system_history = [{
            "cpu_percent": 10.0,
            "memory_percent": 20.0,
            "timestamp": time.time()
        }]
        
        assert analytics.calculate_health_score() == 100
        
    def test_health_score_penalties(self):
        """Test penalties for high load."""
        db_mock = MagicMock()
        analytics = INDBAnalytics(db_mock)
        
        # High Memory (>90%) -> -40 penalty
        analytics.system_history = [{
            "cpu_percent": 10.0,
            "memory_percent": 95.0,
            "timestamp": time.time()
        }]
        
        score = analytics.calculate_health_score()
        assert score == 60 # 100 - 40
        
    def test_oom_prediction_stable(self):
        """Test prediction with stable memory."""
        db_mock = MagicMock()
        analytics = INDBAnalytics(db_mock)
        
        # Inject 20 stable points
        base_time = time.time() - 1000
        for i in range(20):
            analytics.system_history.append({
                "cpu_percent": 10.0,
                "memory_percent": 50.0, # Constant
                "timestamp": base_time + (i * 10)
            })
            
        pred = analytics.predict_oom(minutes=5)
        
        assert pred["risk"] == "low"
        assert abs(pred["trend_slope"]) < 0.001
        
    def test_oom_prediction_critical(self):
        """Test prediction with rising memory."""
        db_mock = MagicMock()
        analytics = INDBAnalytics(db_mock)
        
        # Inject fast rising memory (50% -> 90% in 20 steps)
        base_time = time.time() - 200 # last 200 seconds (10s interval)
        for i in range(20):
            analytics.system_history.append({
                "cpu_percent": 10.0,
                "memory_percent": 50.0 + (i * 2.0), # +2% every 10s
                "timestamp": base_time + (i * 10)
            })
            
        pred = analytics.predict_oom(minutes=5)
        
        # Slope is ~0.2 per sec? No.
        # i=0: 50%, t=-200
        # i=19: 88%, t=-10
        # Rise of 38% over 190s -> 0.2% per sec
        # 5 mins = 300s. 300 * 0.2 = 60%. 88 + 60 = 148% -> Critical
        
        assert pred["risk"] in ["high", "critical"]
        assert pred["predicted_memory_5min"] > 95.0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
